from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .exceptions import OnyoInvalidRepoError, OnyoProtectedPathError
from .git import GitRepo
from .ui import ui
from .utils import get_asset_content, write_asset_file

if TYPE_CHECKING:
    from typing import Iterable, List

log: logging.Logger = logging.getLogger('onyo.onyo')


class OnyoRepo(object):
    r"""
    An object representing an Onyo repository.

    Allows identifying and working with asset paths and directories, getting and
    setting onyo config information.

    Attributes
    ----------
    git: GitRepo
        Contains the path to the root of the repository, and functions to add
        and commit changes, set and get config information, and delete files and
        folders.

    dot_onyo: Path
        The path to the `.onyo/` directory containing templates, the config file
        and other onyo specific information.
    """

    ONYO_DIR = Path('.onyo')
    ONYO_CONFIG = ONYO_DIR / 'config'
    TEMPLATE_DIR = ONYO_DIR / 'templates'
    ANCHOR_FILE_NAME = '.anchor'
    ASSET_DIR_FILE_NAME = '.onyo-asset-dir'
    IGNORE_FILE_NAME = '.onyoignore'

    def __init__(self,
                 path: Path,
                 init: bool = False,
                 find_root: bool = False) -> None:
        r"""Instantiates an `OnyoRepo` object with `path` as the root directory.

        Parameters
        ----------
        path
            An absolute path to the root of the Onyo Repository for which the
            `OnyoRepo` object should be initialized.

        init
            If `init=True`, the `path` will be initialized as a git repo and a
            `.onyo/` directory will be created. `find_root=True` must not be
            used in combination with `init=True`.
            Verifies the validity of the onyo repository.

        find_root
            When `find_root=True`, the function searches the root of a
            repository, beginning at `path`.

        Raises
        ------
        ValueError
            If tried to find a repository root and initializing a repository at
            the same time.

        OnyoInvalidRepoError
            If the path to initialize the repository is not a valid path to an
            Onyo repository.
        """
        self.git = GitRepo(path, find_root=find_root)
        self.dot_onyo = self.git.root / self.ONYO_DIR

        if init:
            if find_root:
                raise ValueError("`find_root=True` must not be used with `init=True`")
            # TODO: Remove path?
            self._init(path)
        else:
            if not self.is_valid_onyo_repo():
                raise OnyoInvalidRepoError(f"'{path}' is not a valid Onyo Repository.")

        ui.log_debug(f"Onyo repo found at '{self.git.root}'")

        # caches
        self._asset_paths: list[Path] | None = None

    def set_config(self,
                   name: str,
                   value: str,
                   location: str = 'onyo') -> None:
        r"""Set the configuration option `name` to `value`.

        Parameters
        ----------
        name
          The name of the configuration option to set.
        value
          The value to set for the configuration option.
        location
          The location of the configuration for which the value
          should be set. Standard Git config locations: 'system',
          'global', 'local', and 'worktree'.
          The location 'onyo' is available in addition and refers
          to a committed config file at `OnyoRepo.ONYO_CONFIG`.
          Default: 'onyo'.

        Raises
        ------
        ValueError
          If `location` is unknown.
        """
        loc = self.ONYO_CONFIG if location == 'onyo' else location
        return self.git.set_config(name=name, value=value, location=loc)

    def get_config(self,
                   name: str) -> str | None:
        r"""Get effective value of config `name`.

        This is considering regular git-config locations and checks
        `OnyoRepo.ONYO_CONFIG` as fallback.
        """
        return self.git.get_config(name) or self.git.get_config(name, self.git.root / self.ONYO_CONFIG)

    def get_asset_name_keys(self) -> list[str]:
        r"""Get a list of keys required for generating asset names

        This is extracting names of used keys from the
        ``onyo.assets.filename`` config, which is supposed to be
        a python format string.

        Notes
        -----
        The extraction is relying on every such usage starting with a
        '{', followed by a key name, which is then either closed
        directly via '}' or first followed by some formatting options
        in which case there's '[', '.', '!', etc.
        Note, that '\w' is used to match the key name, which includes
        alphanumeric characters as well as underscores, therefore
        matching python variable name restrictions. This is relevant,
        because we want to get a dict from the YAML and making the
        values available to name generation by passing the dict to a
        format call on the configured string:
        ``config_str.format(**yaml_dict)``
        Hence, keys need to be able to be python variables.

        This comes with a limitation on what formatting can be used in
        the config. Utilizing nested dictionaries, for example, would
        not be possible. Only the toplevel key would be recognized here.

        Returns
        -------
        list of str
          list containing the names of all keys found
        """
        import re
        # Regex for finding key references in a python format string
        # (see notes above):
        search_regex = r"\{(\w+)"
        config_str = self.get_config("onyo.assets.filename")
        return re.findall(search_regex, config_str) if config_str else []

    def get_editor(self) -> str:
        r"""Returns the editor, progressing through onyo, git, $EDITOR, and finally
        fallback to "nano".
        """
        # onyo config setting (from onyo and git config files)
        editor = self.get_config('onyo.core.editor')

        # git config
        if not editor:
            ui.log_debug("onyo.core.editor is not set.")
            editor = self.get_config('core.editor')

        # $EDITOR environment variable
        if not editor:
            ui.log_debug("core.editor is not set.")
            editor = os.environ.get('EDITOR')

        # fallback to nano
        if not editor:
            ui.log_debug("$EDITOR is also not set.")
            editor = 'nano'

        return editor

    def clear_cache(self) -> None:
        r"""Clear cache of this instance of GitRepo.

        Caches cleared are:
        - `OnyoRepo.asset_paths`
        - `GitRepo.git.clear_cache()`

        If the repository is exclusively modified via public API functions, the
        cache of the `OnyoRepo` object is consistent. If the repository is
        modified otherwise, use of this function may be necessary to ensure that
        the cache does not contain stale information.
        """
        self._asset_paths = None
        self.git.clear_cache()

    @staticmethod
    def generate_commit_message(format_string: str,
                                max_length: int = 80,
                                **kwargs) -> str:
        r"""Generate a commit message subject.

        The function will shorten paths in the resulting string in order to try to fit into
        `max_length`.

        Parameters
        ----------
        format_string
            A format string defining the commit message subject to generate.

        max_length
            An integer specifying the maximal length for generated commit message subjects.

        **kwargs
            Values to insert into the `format_string`. If values are paths, they will be shortened
            to include as much user readable information as possible.

        Returns
        -------
        str
            A message suitable as a commit message subject.
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

        # return the short version of the commit message
        return message

    @property
    def asset_paths(self) -> list[Path]:
        r"""Get the absolute ``Path``\ s of all assets in this repository.

        This property is cached, and is reset automatically on `OnyoRepo.commit()`.

        If changes are made by different means, use `OnyoRepo.clear_cache()` to
        reset the cache.
        """
        if self._asset_paths is None:
            self._asset_paths = self.get_asset_paths()
        return self._asset_paths

    def is_valid_onyo_repo(self) -> bool:
        r"""Assert whether this is a properly set up onyo repository and has a fully
        populated `.onyo/` directory.

        Returns
        -------
        bool
            True when the repository is complete and valid, otherwise False.
        """
        files = ['config',
                 OnyoRepo.ANCHOR_FILE_NAME,
                 Path(OnyoRepo.TEMPLATE_DIR.name) / OnyoRepo.ANCHOR_FILE_NAME,
                 Path('validation') / OnyoRepo.ANCHOR_FILE_NAME]

        # has expected .onyo structure
        if not all(x.is_file() for x in [self.dot_onyo / f for f in files]):
            return False

        # is a git repository
        if subprocess.run(["git", "rev-parse"],
                          cwd=self.git.root,
                          stdout=subprocess.DEVNULL).returncode != 0:
            return False
        return True

    def _init(self,
              path: Path) -> None:
        r"""Initialize an Onyo repository at `path`.

        Re-init-ing an existing repository is safe. It will not overwrite
        anything; it will raise an exception.

        Parameters
        ----------
        path
            The path where to set up an Onyo repository.
            The directory will be initialized as a git repository (if it is not
            one already), ``.onyo/`` directory created (containing default
            config files, templates, etc.), and everything committed.

        Raises
        ------
        FileExistsError
            If called on e.g. an existing file instead of a valid directory,
            or if called on a directory which already contains a `.onyo/`.

        FileNotFoundError
            If called on a directory which sub-directory path does not exist.
        """

        # Note: Why is this necessary to check? Assuming we call git-init on it,
        # this will repeat that same test anyway (and would fail telling us this
        # problem) target must be a directory
        if path.exists() and not path.is_dir():
            raise FileExistsError(f"'{path}' exists but is not a directory.")

        # Note: Why is this a requirement? What could go wrong with mkdir-p ?
        # parent must exist
        if not path.parent.exists():
            raise FileNotFoundError(f"'{path.parent}' does not exist.")

        # Note: Why is this a requirement? Why not only add what's missing in
        # case of apparent re-init? cannot already be an .onyo repo
        dot_onyo = path / '.onyo'
        if dot_onyo.exists():
            raise FileExistsError(f"'{dot_onyo}' already exists.")

        self.git.maybe_init()

        # Note: pheewww - No. Installed resource needs to be found differently.
        #       Who the hell is supposed to maintain that? One cannot simply
        #       move this function without changing its implementation.
        skel_dir = Path(__file__).resolve().parent.parent / 'skel'

        # populate .onyo dir
        shutil.copytree(skel_dir, self.dot_onyo)

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

        Returns
        -------
        bool
          True if `path` is used internally by onyo.
        """
        return path == self.dot_onyo or self.dot_onyo in path.parents or \
            path.name.startswith('.onyo') or path.name == self.ANCHOR_FILE_NAME

    def is_inventory_dir(self,
                         path: Path) -> bool:
        r"""Whether `path` is an inventory directory.

        This only considers directories w/ committed anchor file.
        """
        return path == self.git.root or \
            (self.is_inventory_path(path) and path / self.ANCHOR_FILE_NAME in self.git.files)

    def is_asset_path(self,
                      path: Path) -> bool:
        r"""Whether `path` is an asset in the repository.

        Parameters
        ----------
        path
          Path to check for pointing to an asset.

        Returns
        -------
        bool
          Whether `path` is an asset in the repository.
        """
        return path in self.asset_paths

    def is_inventory_path(self,
                          path: Path) -> bool:
        r"""Whether `path` is valid for tracking an asset or an inventory directory.

        This only checks whether `path` is suitable in principle.
        It does not check whether that path already exists or if it would be valid
        and available as an asset name.

        Parameters
        ----------
        path
          Path to check.

        Returns
        -------
        bool
          Whether `path` is valid for an inventory item.
        """
        return path.is_relative_to(self.git.root) and \
            not self.git.is_git_path(path) and \
            not self.is_onyo_path(path) and \
            not self.is_onyo_ignored(path)

    def is_asset_dir(self, path: Path) -> bool:
        r"""Whether `path` is an asset directory.

        An asset directory is both, an asset and an inventory directory.

        Parameters
        ----------
        path
          Path to check.

        Returns
        -------
        bool
          Whether `path` is an asset directory.
        """
        return self.is_inventory_dir(path) and self.is_asset_path(path)

    def is_onyo_ignored(self, path: Path) -> bool:
        r"""Whether `path` is matched by an ``.onyoignore`` file.

        Such a path would be tracked by git, but not considered
        to be an inventory item by onyo.
        Ignore files do apply to the subtree they are placed into.

        Parameters
        ----------
        path
          Path to check for matching an exclude pattern in an ignore
          file (`OnyoRepo.IGNORE_FILE_NAME`).

        Returns
        -------
        bool
          Whether `path` is ignored.
        """
        candidates = [self.git.root / p / OnyoRepo.IGNORE_FILE_NAME
                      for p in path.relative_to(self.git.root).parents]
        actual = [f for f in candidates if f in self.git.files]  # committed files only
        for ignore_file in actual:
            if path in self.git.check_ignore(ignore_file, [path]):
                return True
        return False

    def get_template(self,
                     path: Path | str | None = None) -> dict:
        r"""Select a template file and return an asset dict from it.
         from the directory `.onyo/templates/`

        Parameters
        ----------
        path
            Template file. If this a relative path or a string, then this
            is interpreted as relative to the template directory.
            If no path is given, the template defined in the config file
            `.onyo/config` is returned.

        Returns
        -------
        dict
            dictionary representing the content of the template. If `name`
            is not specified and there's no `onyo.new.template` config set
            the dictionary will be empty.

        Raises
        ------
        ValueError
            If the requested template can't be found or is not a file.
        """
        if not path:
            path = self.get_config('onyo.new.template')
            if path is None:
                return dict()
        template_file = self.git.root / self.TEMPLATE_DIR / path \
            if isinstance(path, str) or not path.is_absolute() \
            else path
        if not template_file.is_file():
            raise ValueError(f"Template {path} does not exist.")
        return get_asset_content(template_file)

    def validate_anchors(self) -> bool:
        r"""Check if all dirs (except those in `.onyo/`) contain an .anchor file.

        Returns
        -------
        bool
            True if all directories contain an `.anchor` file, otherwise False.
        """
        # Note: First line not using protected_paths, because `.anchor` is part
        #       of it. But ultimately, exist vs expected should take the same
        #       subtrees into account. So - not good to code it differently.
        anchors_exist = {x
                         for x in self.git.files
                         if x.name == self.ANCHOR_FILE_NAME and
                         self.is_inventory_path(x.parent)}

        anchors_expected = {Path(x) / self.ANCHOR_FILE_NAME
                            for x in [self.git.root / f for f in self.git.root.glob('**/')]
                            if x != self.git.root and self.is_inventory_path(x) and x.is_dir()}
        difference = anchors_expected.difference(anchors_exist)

        if difference:
            log.warning(
                'The following .anchor files are missing:\n'
                '{0}'.format('\n'.join(map(str, difference))))
            log.warning(
                "Likely 'mkdir' was used to create the directory. Use "
                "'onyo mkdir' instead.")
            # TODO: Prompt the user if they want Onyo to fix it.

            return False

        return True

    def get_asset_paths(self,
                        subtrees: Iterable[Path] | None = None,
                        depth: int = 0) -> List[Path]:
        r"""Select all assets in the repository that are relative to the given
        `subtrees` descending at most `depth` directories.

        Parameters
        ----------
        subtrees
          Paths to look for assets under. Defaults to the root of the inventory.
        depth
          Number of levels to descend into. Must be greater equal 0.
          If 0, descend recursively without limit. Defaults to 0.

        Returns
        -------
          list of Path
            Paths to all matching assets in the repository.
        """
        if depth < 0:
            raise ValueError(f"depth must be greater or equal 0, but is '{depth}'")
        # Note: The if-else here doesn't change result, but utilizes `GitRepo`'s cache:
        files = self.git.get_subtrees(subtrees) if subtrees else self.git.files
        if depth:
            roots = subtrees if subtrees else [self.git.root]
            files = [f
                     for f in files
                     for r in roots
                     if r in f.parents and len(f.parents) - len(r.parents) <= depth]

        # This only checks for `is_inventory_path`, since we already
        # know it's a committed file:
        return [f for f in files if self.is_inventory_path(f)] + \
               [f.parent for f in files if f.name == self.ASSET_DIR_FILE_NAME]

    def get_asset_content(self,
                          path: Path) -> dict:
        r"""Get a dictionary representing `path`'s content.

        Parameters
        ----------
        path
          Asset path to load. This is expected to be either a YAML file
          or an asset directory (`OnyoRepo.ASSET_DIR_FILE_NAME`
          automatically appended).

        Returns
        -------
        dict
          Dictionary representing an asset. That is: The union of the
          content of the YAML file and teh asset's pseudo-keys.
        """
        if not self.is_asset_path(path):
            raise ValueError(f"{path} is not an asset path")
        if self.is_inventory_dir(path):
            # It's an asset and an inventory dir -> asset dir
            a = get_asset_content(path / self.ASSET_DIR_FILE_NAME)
            a['is_asset_directory'] = True
        else:
            a = get_asset_content(path)
            a['is_asset_directory'] = False
        # Add pseudo-keys:
        a['path'] = path
        a['directory'] = path.parent
        return a

    def write_asset_content(self,
                            asset: dict) -> dict:
        path = asset.get('path')
        if not path:
            raise RuntimeError("Trying to write asset to unknown path")
        if self.is_inventory_path(path):
            if asset.get('is_asset_directory', False) and path.name != self.ASSET_DIR_FILE_NAME:
                path = path / self.ASSET_DIR_FILE_NAME
            write_asset_file(path, asset)
        else:
            raise ValueError(f"{path} is not a valid inventory path")

        # TODO: Potentially return/modify updated (pseudo-keys: last modified, etc.!) asset dict.
        return asset

    def mk_inventory_dirs(self,
                          dirs: Iterable[Path] | Path) -> list[Path]:
        r"""Create inventory directories `dirs`.

        Creates `dirs` including anchor files.

        Raises
        ------
        OnyoProtectedPathError
          if `dirs` contains an invalid path (see
          `OnyoRepo.is_inventory_path()`).

        FileExistsError
          if `dirs` contains a path pointing to an existing file (hence, the
          dir can't be created).

        Returns
        -------
        list of Path
          list of created anchor files (paths to be committed).
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
        anchors = {i / OnyoRepo.ANCHOR_FILE_NAME for d in dirs
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

    def commit(self, paths: Iterable[Path] | Path, message: str):
        r"""Commit changes to the repository.

        This is resets the cache and is otherwise just a proxy for
        `GitRepo.commit`.

        Parameters
        ----------
        paths
          List of paths to commit.
        message
          The git commit message.
        """
        self.git.commit(paths=paths, message=message)
        self.clear_cache()
