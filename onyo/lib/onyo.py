from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .consts import (
    ANCHOR_FILE_NAME,
    ASSET_DIR_FILE_NAME,
    IGNORE_FILE_NAME,
    KNOWN_REPO_VERSIONS,
    ONYO_CONFIG,
    ONYO_DIR,
    TEMPLATE_DIR,
)
from .exceptions import (
    NotAnAssetError,
    OnyoInvalidRepoError,
    OnyoProtectedPathError
)
from .git import GitRepo
from .ui import ui
from .utils import (
    DotNotationWrapper,
    get_asset_content,
    write_asset_file,
)

if TYPE_CHECKING:
    from typing import (
        Generator,
        Iterable,
        List,
        Literal,
    )
    from collections import UserDict

log: logging.Logger = logging.getLogger('onyo.onyo')


class OnyoRepo(object):
    r"""Representation of an Onyo repository.

    Identify and work with asset paths and directories. Get and set onyo config
    information.

    Attributes
    ----------
    git
        Reference to the :py:class:`onyo.lib.git.GitRepo` of this Onyo
        repository.
    dot_onyo
        The Path of the ``.onyo/`` subdirectory (:py:data:`Onyo_DIR`) that
        contains templates, the onyo-config file, and other onyo-relevant files.
    """

    def __init__(self,
                 path: Path,
                 init: bool = False,
                 find_root: bool = False) -> None:
        r"""Instantiate an ``OnyoRepo`` object with ``path`` as the root directory.

        Parameters
        ----------
        path
            An absolute path to the root of the Onyo Repository.
        init
            Initialize ``path`` as a git repo and create/populate the subdir
            ``.onyo/``. Cannot be used with ``find_root=True``.
        find_root
            Search for the root of the repository beginning at ``path``, and
            then up through parents. Cannot be used with ``init==True``.

        Raises
        ------
        ValueError
            ``find_root=True`` and ``init==True`` both specified.
        OnyoInvalidRepoError
            ``path`` is not a valid path to an Onyo repository.
        """

        self.git = GitRepo(path, find_root=find_root)
        self.dot_onyo = self.git.root / ONYO_DIR
        self.template_dir = self.git.root / TEMPLATE_DIR
        self.onyo_config = self.git.root / ONYO_CONFIG

        if init:
            if find_root:
                raise ValueError("`find_root=True` must not be used with `init=True`")
            # TODO: Remove path?
            self._init(path)
        else:
            self.validate_onyo_repo()

        self.version = self.git.get_config('onyo.repo.version', self.onyo_config)
        ui.log_debug(f"Onyo repo (version {self.version}) found at '{self.git.root}'")

        # caches
        self._asset_paths: list[Path] | None = None
        self._config_cache: dict[str, dict[str, str]] = {'git': {}, 'onyo': {}}

    def set_config(self,
                   key: str,
                   value: str,
                   location: Literal['system', 'global', 'local', 'worktree', 'onyo'] = 'onyo'
                  ) -> None:
        r"""Set the value of a configuration key.

        Parameters
        ----------
        key
            The name of the configuration key to set.
        value
            The value to set the configuration key to.
        location
            The location to set the key/value in. Valid locations are standard
            git-config locations (``'system'``, ``'global'``, ``'local'``, and
            ``'worktree'``) and ``'onyo'`` (:py:data:`onyo.lib.consts.ONYO_CONFIG`).

        Raises
        ------
        ValueError
            ``location`` is invalid.
        """

        # repo version shim
        if self.version == '1' and key == 'onyo.assets.name-format':
            key = 'onyo.assets.filename'

        # clear the config cache
        self._config_cache = {'git': {}, 'onyo': {}}

        # set
        loc = ONYO_CONFIG if location == 'onyo' else location
        return self.git.set_config(key=key, value=value, location=loc)

    def get_config(self,
                   key: str) -> str | None:
        r"""Get the effective value of a configuration key.

        This first checks git's normal git-config locations and then
        :py:data:`onyo.lib.consts.ONYO_CONFIG` as a fallback.

        The results are cached, which are cleared automatically by
        :py:func:`commit` and :py:func:`set_config`.

        If changes are made by other means, use :py:func:`clear_cache` to reset
        the cache.

        Parameters
        ----------
        key
            Name of the configuration key to query. Follows Git's convention
            of "SECTION.NAME.KEY" to address a key in a git config file::

              [SECTION "NAME"]
                  KEY = VALUE
        """

        value = None

        # repo version shim
        if self.version == '1' and key == 'onyo.assets.name-format':
            key = 'onyo.assets.filename'

        #
        # check cache
        #
        cache_hit = False

        try:
            # git
            value = self._config_cache['git'][key]
            ui.log_debug(f"config '{key}' acquired from cache of git config: '{value}'")
            cache_hit = True
        except KeyError:
            cache_hit = False
            pass

        if value is None:
            # onyo
            try:
                value = self._config_cache['onyo'][key]
                ui.log_debug(f"config '{key}' acquired from cache of onyo config: '{value}'")
                cache_hit = True
            except KeyError:
                cache_hit = False
                pass

        if cache_hit:
            return value

        #
        # query actual config files
        #
        ui.log_debug(f"config '{key}' cache miss")

        # query the full git config stack
        value = self.git.get_config(key)
        self._config_cache['git'][key] = value  # pyre-ignore[6]

        if value is not None:
            return value

        # query .onyo/config
        value = self.git.get_config(key, self.onyo_config)
        self._config_cache['onyo'][key] = value  # pyre-ignore[6]

        return value

    @property
    def auto_message(self) -> bool:
        r"""The configured value of ``onyo.commit.auto-message``."""

        raw = self.get_config("onyo.commit.auto-message")
        if raw:
            from_cfg = raw.strip().lower()
            if from_cfg in ["true", "1"]:
                return True
            if from_cfg in ["false", "0"]:
                return False

            ui.log(f"Invalid config value \"{raw}\" for 'onyo.commit.auto-message'. Using default \"true\".",
                   level=logging.WARNING)

        # default - applies if config isn't set or has an invalid value
        return True

    def get_asset_name_keys(self) -> list[str]:
        r"""Get a list of keys used to generate asset names.

        Key names are extracted from the format string specified in the config
        ``onyo.assets.name-format``.
        """

        import re

        # Notes regarding the regex:
        # The extraction relies on a '{', followed by a key name, which is then
        # either closed directly via '}' or followed by formatting options
        # (e.g. '[', '.', '!', etc).
        # The use of '\w' to match the key name is important, as it includes
        # alphanumeric characters as well as underscores. This matches Python's
        # variable name restrictions), which is necessary because we pass the
        # asset dict to a format call on the configured string:
        # `config_str.format(**yaml_dict)`
        # Thus, keys need to be able to be python variables.
        #
        # This limits somewhat the formatting that can be used in the config.
        # Nested dictionaries are (for example) not possible.
        # Instead, dotnotation should be used (e.g. model.name).
        search_regex = r"\{([\w\.]+)"  # TODO: temp. fix to include `.`. Revert with full dict support
        config_str = self.get_config("onyo.assets.name-format")

        return re.findall(search_regex, config_str) if config_str else []

    def get_editor(self) -> str:
        r"""Return the editor to use.

        This progresses through: 1) ``onyo.core.editor`` 2) git's ``core.editor``
        3) ``EDITOR`` environmental variable and 4) "nano" (fallback).
        """

        from os import environ

        # onyo config setting (from onyo and git config files)
        editor = self.get_config('onyo.core.editor')

        # git config
        if not editor:
            ui.log_debug("onyo.core.editor is not set.")
            editor = self.get_config('core.editor')

        # $EDITOR environment variable
        if not editor:
            ui.log_debug("core.editor is not set.")
            editor = environ.get('EDITOR')

        # fallback to nano
        if not editor:
            ui.log_debug("$EDITOR is also not set.")
            editor = 'nano'

        return editor

    def clear_cache(self) -> None:
        r"""Clear the cache of this instance of OnyoRepo (and the sub-:py:class:`onyo.lib.git.GitRepo`).

        When the repository is modified using only the public API functions, the
        cache is consistent. This method is only necessary if the repository is
        modified otherwise.
        """

        self._asset_paths = None
        self._config_cache = {'git': {}, 'onyo': {}}
        self.git.clear_cache()

    @staticmethod
    def generate_commit_subject(format_string: str,
                                max_length: int = 80,
                                **kwargs) -> str:
        r"""Generate a commit message subject.

        Path names are shortened on a best effort basis to reduce the subject
        length to ``max_length``.

        Parameters
        ----------
        format_string
            A format string defining the commit message subject to generate.
        max_length
            The suggested max length for the generated commit message subject.
        **kwargs
            Values to insert into the ``format_string``. Values that are Paths
            will be shortened as needed.
        """

        # long message: full paths
        shortened_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, list):
                shortened_kwargs[key] = ','.join([str(x) for x in value])
            else:
                shortened_kwargs[key] = str(value)

        message = format_string.format(**shortened_kwargs)
        if len(message) < max_length:
            return message

        # shorter message: highest level (e.g. dir or asset name)
        shortened_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, list):
                shortened_kwargs[key] = ','.join([x.name if isinstance(x, Path) else
                                                  str(x) for x in value])
            elif isinstance(value, Path):
                shortened_kwargs[key] = value.name
            else:
                shortened_kwargs[key] = str(value)

        message = format_string.format(**shortened_kwargs)
        return message

    @property
    def asset_paths(self) -> list[Path]:
        r"""Get the absolute ``Path``\ s of all assets in this repository.

        This property is cached and is reset automatically on :py:func:`commit`.

        If changes are made by other means, use :py:func:`clear_cache` to reset
        the cache.
        """

        if self._asset_paths is None:
            self._asset_paths = self.get_item_paths(types=['assets'])

        return self._asset_paths

    def validate_onyo_repo(self) -> None:
        r"""Assert whether this a full init-ed onyo repository.

        Raises
        ------
        OnyoInvalidRepoError
            Validation failed
        """

        files = ['config',
                 ANCHOR_FILE_NAME,
                 self.template_dir / ANCHOR_FILE_NAME,
                 Path('validation') / ANCHOR_FILE_NAME]

        # has expected .onyo structure
        if not all(x.is_file() for x in [self.dot_onyo / f for f in files]):
            # TODO: Make fsck fix that and hint here
            raise OnyoInvalidRepoError(f"'{self.dot_onyo}' does not have expected structure.")

        # TODO: This should automatically at the level of `GitRepo` instead.
        # is a git repository
        if subprocess.run(["git", "rev-parse"],
                          cwd=self.git.root,
                          stdout=subprocess.DEVNULL).returncode != 0:
            raise OnyoInvalidRepoError(f"'{self.git.root} is not a git repository")

        # has a known repo version
        version = self.git.get_config('onyo.repo.version', self.onyo_config)
        if version not in KNOWN_REPO_VERSIONS:
            raise OnyoInvalidRepoError(f"Unknown onyo repository version '{version}'")

    def _init(self,
              path: Path) -> None:
        r"""Initialize an Onyo repository at ``path``.

        Re-init-ing an existing repository will raise an exception and not alter
        anything.

        Parameters
        ----------
        path
            Path where to create an Onyo repository.
            The directory will be initialized as a git repository (if it is not
            one already), the ``.onyo/`` directory created (containing default
            config files, templates, etc.), and everything committed.

        Raises
        ------
        FileExistsError
            ``path`` is a file or an Onyo repo (specifically: contains the
            subdir ``.onyo/``).
        FileNotFoundError
            ``path`` is a directory whose parent does not exist.
        """

        from importlib import resources

        # Note: Why not upgrade/heal/no-op for a re-init?
        # cannot already be an .onyo repo
        dot_onyo = path / '.onyo'
        if dot_onyo.exists():
            raise FileExistsError(f"'{dot_onyo}' already exists.")

        self.git.init_without_reinit()

        # populate .onyo dir
        with resources.path("onyo", "skel") as skel_dir:
            shutil.copytree(skel_dir, self.dot_onyo)

        # set default config if it's not set already
        if self.git.get_config(key="onyo.commit.auto-message",
                               path=ONYO_CONFIG) is None:
            self.git.set_config(key="onyo.commit.auto-message",
                                value="true",
                                location=ONYO_CONFIG)

        # add and commit
        self.commit(self.dot_onyo,
                    message='Initialize as an Onyo repository')
        ui.print(f'Initialized empty Onyo repository in {self.dot_onyo}/')

    def is_onyo_path(self,
                     path: Path) -> bool:
        r"""Determine whether an absolute `path` is used by onyo internally.

        Currently anything underneath `.onyo/`, anything named `.onyo*`,
        and an anchor files in an inventory directory is considered an
        onyo path.

        Parameters
        ----------
        path
          The path to check.
        """

        return path == self.dot_onyo or self.dot_onyo in path.parents or \
            path.name.startswith('.onyo') or path.name == ANCHOR_FILE_NAME

    def is_asset_dir(self,
                     path: Path) -> bool:
        r"""Whether ``path`` is an asset directory.

        An asset directory is both an asset and an inventory directory.

        Parameters
        ----------
        path
            Path to check.
        """

        return self.is_inventory_dir(path) and self.is_asset_path(path)

    def is_asset_file(self,
                      path: Path) -> bool:
        r"""Whether ``path`` is an asset file.

        Parameters
        ----------
        path
            Path to check.
        """

        return not self.is_inventory_dir(path) and self.is_asset_path(path)

    def is_asset_path(self,
                      path: Path) -> bool:
        r"""Whether ``path`` is an asset in the repository.

        Parameters
        ----------
        path
            Path to check.
        """

        return path in self.asset_paths

    def is_inventory_dir(self,
                         path: Path) -> bool:
        r"""Whether ``path`` is an inventory directory.

        This only considers directories with a committed anchor file.

        Parameters
        ----------
        path
            Path to check.
        """

        return path == self.git.root or \
            (self.is_inventory_path(path) and path / ANCHOR_FILE_NAME in self.git.files)

    # TODO: the name of this function is a mismatch with its functionality
    #       compared to the other is_inventory_*() functions. This should be
    #       remedied.
    def is_inventory_path(self,
                          path: Path) -> bool:
        r"""Whether ``path`` a valid potential name for an asset or an inventory directory.

        This only checks whether ``path`` is suitable in principle.
        It does not check whether that path already exists or if it would be valid
        and available as an asset name.

        Parameters
        ----------
        path
            Path to check.
        """

        return self.git.root in path.parents and \
            not self.git.is_git_path(path) and \
            not self.is_onyo_path(path) and \
            not self.is_onyo_ignored(path)

    def is_item_path(self,
                     path: Path) -> bool:
        r"""Whether ``path`` is a valid path for an item.

        This checks whether ``path`` is valid for reading an item from
        or creating an item at in principle.
        It's not checking whether ``path`` actually exists.
        """

        return path == self.git.root or self.is_inventory_path(path) or self.is_template_path(path)

    def is_template_path(self,
                         path: Path) -> bool:
        r"""Whether ``path`` is a valid template location."""

        return not self.is_onyo_ignored(path) and \
            not self.git.is_git_path(path) and \
            (self.template_dir == path) or (self.template_dir in path.parents)

    def is_onyo_ignored(self,
                        path: Path) -> bool:
        r"""Whether ``path`` is matched by a pattern in ``.onyoignore``.

        Such a path would not considered to be an inventory item by Onyo, but
        could still be tracked in git.

        ``.onyoignore`` files apply to the subtree they are placed into.

        Parameters
        ----------
        path
            Path to check for matching an exclude pattern in an ignore
            file (:py:data:`onyo.lib.consts.IGNORE_FILE_NAME`).
        """

        candidates = [self.git.root / p / IGNORE_FILE_NAME
                      for p in path.relative_to(self.git.root).parents]
        actual = [f for f in candidates if f in self.git.files]  # committed files only
        for ignore_file in actual:
            if path in self.git.check_ignore(ignore_file, [path]):
                return True

        return False

    def get_template(self,
                     path: Path | str | None = None) -> dict:
        r"""Select a template file and return an asset dict from it.

        Parameters
        ----------
        path
            Path to a Template. If relative or a string, then it is considered
            as relative to the template directory (:py:data:`onyo.lib.consts.TEMPLATE_DIR`).
            If no path is given, the template defined in the config
            ``onyo.new.template`` is used.

        If ``name`` is not specified and the config ``onyo.new.template`` is not
        set, the dictionary will be empty.

        Raises
        ------
        ValueError
            If the requested template can't be found.
        """

        if not path:
            path = self.get_config('onyo.new.template')
            if path is None:
                return dict()

        template_file = self.template_dir / path \
            if isinstance(path, str) or not path.is_absolute() \
            else path
        if not template_file.is_file():
            raise ValueError(f"Template {path} does not exist.")

        return get_asset_content(template_file)

    def validate_anchors(self) -> bool:
        r"""Check if all inventory directories contain an ``.anchor`` file.

        Returns
        -------
        bool
            True if all directories contain an ``.anchor`` file, otherwise False.
        """

        # Note: First line not using protected_paths, because `.anchor` is part
        #       of it. But ultimately, exist vs expected should take the same
        #       subtrees into account. So - not good to code it differently.
        anchors_exist = {x
                         for x in self.git.files
                         if x.name == ANCHOR_FILE_NAME and
                         self.is_inventory_path(x.parent)}
        anchors_expected = {Path(x) / ANCHOR_FILE_NAME
                            for x in [self.git.root / f for f in self.git.root.glob('**/')]
                            if x != self.git.root and self.is_inventory_path(x) and x.is_dir()}

        difference = anchors_expected.difference(anchors_exist)
        if difference:
            ui.log("The following .anchor files are missing:\n"
                   "{0}\nLikely 'mkdir' was used to create the directory."
                   "Use 'onyo mkdir' instead.".format('\n'.join(map(str, difference))),
                   level=logging.WARNING)
            # TODO: Prompt the user if they want Onyo to fix it.
            return False

        return True

    def get_item_paths(self,
                       include: Iterable[Path] | None = None,
                       exclude: Iterable[Path] | Path | None = None,
                       depth: int = 0,
                       types: List[Literal['assets', 'directories']] | None = None,
                       intermediates: bool = True
                       ) -> List[Path]:
        r"""Get the Paths of all items matching paths and filters.

        Parameters
        ----------
        include
            Paths under which to look for items. Default is to inventory root.
        exclude
            Paths to exclude (i.e. items underneath will not be returned).
        depth
            Number of levels to descend into the directories specified by
            ``include``. A depth of ``0`` descends recursively without limit.
        types
            List of types of inventory items to consider. Equivalent to
            ``onyo.is.asset=True`` and ``onyo.is.directory=True``.
            Default is ``['assets']``.
        intermediates
            Return intermediate directory items. If ``False``, the only directories
            explicitly contained in the returned list are leaves.
        """

        if types is None:
            types = ['assets']
        if include is None:
            include = [self.git.root]
        if depth < 0:
            raise ValueError(f"depth must be greater or equal 0, but is '{depth}'")

        exclude = [exclude] if isinstance(exclude, Path) else exclude
        if not any(self.is_template_path(p) for p in include):
            # if no template dir is explicitly given, remove the template subdir entirely:
            if exclude:
                exclude.append(self.template_dir)  # pyre-ignore[16]
            else:
                exclude = [self.template_dir]

        files = self.git.get_files(include)

        if depth:
            files = [f
                     for f in files
                     for root in include
                     if root in f.parents and (len(f.parents) - len(root.parents) <= depth)]
        if exclude:
            files = [f for f in files if all(f != p and p not in f.parents for p in exclude)]

        paths = []
        # special case root - has no anchor file that would show up in `files`:
        if "directories" in types and self.git.root in include:
            paths.append(self.git.root)

        for f in files:
            if "assets" in types and f.name == ASSET_DIR_FILE_NAME:
                if f.parent not in paths:
                    paths.append(f.parent)
                continue
            if "assets" in types and f.name != ANCHOR_FILE_NAME and self.is_item_path(f):
                paths.append(f)
                continue
            if "directories" in types and f.name == ANCHOR_FILE_NAME and self.is_item_path(f.parent):
                if f.parent not in paths:
                    paths.append(f.parent)
                continue

        if not intermediates:
            # remove any directory that has children in `paths` and is not an asset dir
            for p in [p for p in paths if
                      (p / ASSET_DIR_FILE_NAME not in files) and any(i.parent == p for i in paths)]:
                paths.remove(p)

        return paths

    def get_asset_content(self,
                          path: Path) -> dict:
        r"""Get a dictionary representing ``path``'s content.

        The content also includes the asset's pseudo-keys.

        Parameters
        ----------
        path
            Path of asset to load. This may be either a YAML file or an
            Asset Directory (:py:data:`onyo.lib.consts.ASSET_DIR_FILE_NAME` is automatically
            appended).
        """

        if not self.is_asset_path(path):
            raise NotAnAssetError(f"{path} is not an asset path")

        try:
            # TODO: Where do we make sure to distinguish onyo.path.file from onyo.path.relative?
            #       Surely outside, but consider this!
            a = get_asset_content((path / ASSET_DIR_FILE_NAME) if self.is_inventory_dir(path) else path)
        except NotAnAssetError as e:
            raise NotAnAssetError(f"{str(e)}\n"
                                  f"If {path} is not meant to be an asset, consider putting it into"
                                  f" '{IGNORE_FILE_NAME}'") from e

        return a

    def write_asset_content(self,
                            asset: dict | UserDict) -> dict | UserDict:
        r"""Write an asset's contents to disk.

        The correct path is determined using the asset's pseudo-keys.

        Parameters
        ----------
        asset
            The asset dict to write.
        """

        path = asset.get('onyo.path.absolute')
        if not path:
            raise RuntimeError("Cannot write asset to an unspecified path")

        if self.is_inventory_path(path):
            if asset.get('onyo.is.directory') and path.name != ASSET_DIR_FILE_NAME:
                path = path / ASSET_DIR_FILE_NAME
            write_asset_file(path, asset)
        else:
            raise ValueError(f"{path} is not a valid inventory path")

        # TODO: Potentially return/modify updated (pseudo-keys: last modified, etc.!) asset dict.
        return asset

    def mk_inventory_dirs(self,
                          dirs: Iterable[Path] | Path) -> list[Path]:
        r"""Create inventory directories.

        Also creates an ``.anchor`` file for each new directory.

        A list of the newly-created anchor files is returned.

        Raises
        ------
        OnyoProtectedPathError
            ``dirs`` contains an invalid path.
        FileExistsError
            ``dirs`` contains a path pointing to an existing file
        """

        if isinstance(dirs, Path):
            dirs = [dirs]

        non_inventory_paths = [d for d in dirs if not self.is_inventory_path(d)]
        if non_inventory_paths:
            raise OnyoProtectedPathError(
                'The following paths are protected by onyo:\n{}\nNo '
                'directories were created.'.format(
                    '\n'.join(map(str, non_inventory_paths))))

        # Note: This check is currently done here, because we are dealing with a
        # bunch of directories at once. We may want to operate on single dirs,
        # rely on mkdir throwing instead, and collect errors higher up.
        file_paths = [d for d in dirs if d.is_file()]
        if file_paths:
            raise FileExistsError(
                'The following paths are existing files:\n{}\nNo directories '
                'were created.'.format(
                    '\n'.join(map(str, file_paths))))

        # make dirs
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # anchors
        anchors = {i / ANCHOR_FILE_NAME for d in dirs
                   for i in [d] + list(d.parents)
                   if i.is_relative_to(self.git.root) and
                   not i.samefile(self.git.root)}
        added_files = []
        for a in anchors:
            # Note, that this currently tests for existence first.
            # That's because we return actually modified paths for possible
            # rollback. Eventually, rollback approaches should be stopped
            # wherever possible. Collect what needs doing first instead of do it
            # and then ask for confirmation.
            if not a.exists():
                a.touch(exist_ok=False)
                added_files.append(a)

        return added_files

    def commit(self,
               paths: Iterable[Path] | Path,
               message: str) -> None:
        r"""Commit changes to the repository.

        This is resets the cache and is otherwise just a proxy for
        :py:func:`onyo.lib.git.GitRepo.commit`.

        Parameters
        ----------
        paths
            List of Paths to commit.
        message
            The git commit message.
        """

        self.git.commit(paths=paths, message=message)
        self.clear_cache()

    def get_history(self,
                    path: Path | None = None,
                    n: int | None = None) -> Generator[UserDict, None, None]:
        r"""Yield the history of Inventory Operations for a path.

        Parameters
        ----------
        path
            The Path to get the history of. Defaults to the repo root.
        n
            Limit history to ``n`` commits. ``None`` for no limit (default).
        """

        # TODO: This isn't quite right yet. operations records are defined in Inventory.
        #       But Inventory shouldn't talk to GitRepo directly. So, either pass the record
        #       from Inventory to OnyoRepo and turn it into a commit-message part only,
        #       or have sort of a proxy in OnyoRepo.
        #       -> May be: get_history(Item) in Inventory and get_history(path) in OnyoRepo.
        from onyo.lib.parser import parse_operations_record

        for commit in self.git.history(path, n):
            record = []
            start = False
            for line in commit['message']:
                if line.strip() == "--- Inventory Operations ---":
                    start = True
                if start:
                    record.append(line)

            if record:
                commit['operations'] = parse_operations_record(record)

            yield DotNotationWrapper(commit)
