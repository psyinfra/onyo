from __future__ import annotations

import logging
import shutil
import subprocess
import os
from pathlib import Path
from typing import Iterable, Optional, Union, List, Dict

from ruamel.yaml import YAML  # pyre-ignore[21]

from .ui import ui
from .git import GitRepo
from .exceptions import OnyoInvalidRepoError, OnyoProtectedPathError

log: logging.Logger = logging.getLogger('onyo.onyo')


# TODO: pseudo-key generation mapping
NEW_PSEUDO_KEYS = ['path']  # TODO: name temporary b/c RF (old idea of pseudo-keys doesn't match)


def dict_to_yaml(d: Dict[str, Union[float, int, str]]) -> str:
    content = {k: v for k, v in d.items() if k not in NEW_PSEUDO_KEYS}  # RESERVED_KEYS
    if not content:
        return ""
    from io import StringIO
    yaml = YAML(typ='rt')
    s = StringIO()
    yaml.dump(content,
              s)
    return s.getvalue()


def yaml_to_dict(path: Path) -> dict:
    yaml = YAML(typ='rt', pure=True)
    content = yaml.load(path)  # raises scanner.ScannerError
    # TODO: Exception was caught and printed but didn't interrupt. Double-check why.
    if content is None:
        content = dict()
    return content


class OnyoRepo(object):
    """
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

    asset_paths: list of Path
        The paths to all assets in the Repository.
        This property is cached and consistent when only the public functions of
        OnyoRepo are called. Usage of private or external functions might
        require a manual reset of the cache with `OnyoRepo.clear_caches()`.
    """

    ONYO_DIR = Path('.onyo')
    ONYO_CONFIG = ONYO_DIR / 'config'
    TEMPLATE_DIR = 'templates'
    ANCHOR_FILE = '.anchor'
    ASSET_DIR_FILE = '.onyo-asset-dir'

    def __init__(self,
                 path: Path,
                 init: bool = False,
                 find_root: bool = False) -> None:
        """
        Instantiates an `OnyoRepo` object with `path` as the root directory.

        Parameters
        ----------
        path: Path
            An absolute path to the root of the Onyo Repository for which the
            `OnyoRepo` object should be initialized.

        init: boolean
            If `init=True`, the `path` will be initialized as a git repo and a
            `.onyo/` directory will be created. `find_root=True` must not be
            used in combination with `init=True`.
            Verifies the validity of the onyo repository.

        find_root: boolean
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
            self._init(path)
        else:
            if not self.is_valid_onyo_repo():
                raise OnyoInvalidRepoError(f"'{path}' is no valid Onyo Repository.")

        ui.log_debug(f"Onyo repo found at '{self.git.root}'")

        # caches
        self._asset_paths: Optional[list[Path]] = None

    def get_config(self, name: str) -> Union[str, None]:
        """
        """
        # TODO: lru_cache?
        # TODO: This needs to account for both .onyo/config + all git configs with correct prios
        # Where do we inject onyo/.config in the order of priority?
        # editor tests say git > onyo. Fine for now, but doesn't seem entirely intuitive. Why would a system config take
        # precedence over a committed setting specific to the inventory repo?
        return self.git.get_config(name) or self.git.get_config(name, self.git.root / self.ONYO_CONFIG)

    def get_required_asset_keys(self) -> list[str]:
        """Get a list of keys required for generating asset names

        Name generation is configured by a python format string.
        Hence, this gets the config finds all keys referenced in it.

        Returns
        -------
        list of str
          list containing the names of all keys found
        """
        # Regex for finding key references in a python format string.
        # This is relying on every such usage starting with a '{', followed by a key name, which is then either closed
        # directly via '}' or first followed by some formatting options in which case there's '[', '.', '!', etc.
        # Note, that `\w` should include alphanumeric characters as well as underscores, therefore matching python
        # variable name restrictions. This is relevant, because we want to get a dict from the YAML and making the
        # values available to name generation stored in "onyo.assets.filename" by passing the dict to
        # `config_str.format(**yaml_dict)`.
        # Hence, keys need to be able to be python variables.

        # TODO: Make an issue about implications for usable format strings
        #       (incl. nested dicts in the YAML - possible but not currently supported - wait for usecase)

        search_regex = r"\{(\w+)"

        import re
        config_str = self.get_config("onyo.assets.filename")
        return re.findall(search_regex, config_str) if config_str else []  # TODO: raise, return None or return []?

    def get_editor(self) -> str:
        """
        Returns the editor, progressing through git, onyo, $EDITOR, and finally
        fallback to "nano".
        """
        # onyo config and git config
        editor = self.get_config('onyo.core.editor')

        # $EDITOR environment variable
        if not editor:
            ui.log_debug("onyo.core.editor is not set.")
            editor = os.environ.get('EDITOR')

        # fallback to nano
        if not editor:
            ui.log_debug("$EDITOR is also not set.")
            editor = 'nano'

        return editor

    def clear_caches(self,
                     assets: bool = True) -> None:
        """
        Clear caches of the instance of the repository object.

        Paths such as files, assets, and directories are cached, and can become
        stale when the repository contents are modified. This function clears
        the caches of the properties.

        By default all caches are cleared, and arguments make it possible to
        specify which caches which should remain set.

        If the repository is exclusively modified via public API functions, the
        caches of the `Repo` object are consistent. If the repository is
        modified otherwise, this function clears the caches to ensure that the
        caches do not contain stale information.

        Parameters
        ----------
        assets: boolean
            An option to deactivate or activate the clearing of the
            `asset_paths` cache.
        """
        if assets:
            self._asset_paths = None
            self.git.clear_caches(files=True)

    def generate_commit_message(self,
                                message: Optional[list[str]] = None,
                                cmd: str = "",
                                keys: Optional[list[str]] = None,
                                destination: str = "",
                                max_length: int = 80,
                                modified: Optional[list[Path]] = None) -> str:
        """
        Generate a commit message subject and body suitable for use with
        `git commit`.

        Parameters
        ----------
        message: list of str
            If `message` is given, the function uses the first element of it to
            generate a message subject, and the following ones are joined for
            the message body.

            An optional message to use instead of the generated commit message.
            If multiple elements are given, the first is used as the message
            subject, and the following ones are joined for the message body.
            If no `message` is given, generate a default commit message based on
            the other parameters given, and the `files staged` in the
            repository. The paths for the message are shortened if needed, so
            that the resulting message subject does not exceed `max_length`.

        cmd: str
            Defines the beginning of a commit message subject.

        keys: list of strings
            Allow listing of e.g. changed keys in message subject.
            If given, they are listed at the beginning after `cmd`.

        destination: str
            A string that can specify a destination for the message subject for
            moved assets and directories.

        max_length: int
            An integer specifying the maximal length for generated commit
            message subjects.

        modified: list of paths
            A list of Paths to assets/directories modified in the commit, used
            to generate the commit message subject and body.

        Returns
        -------
        str
            A massage suitable as a commit message for use with `git commit`.
        """
        message = [] if message is None else message
        keys = [] if keys is None else keys
        if modified is None:
            modified = self.git.files_staged

        # ensure uniqueness of modified paths
        modified = list(set(modified))

        message_subject = ""
        message_body = ""
        message_appendix = ""

        # staged files and directories (without ".anchor") in alphabetical order
        changes_to_record = [x if not x.name == self.ANCHOR_FILE else x.parent
                             for x in sorted(f.relative_to(self.git.root) for f in modified)]

        if message:
            message_subject = message[0][0]
            message_body = '\n'.join(map(str, [x[0] for x in message[1:]]))
        else:
            # get variables for the begin of the commit message `msg_dummy`
            dest = None
            keys_str = ""
            if keys:
                keys_str = f" ({','.join(str(x.split('=')[0]) for x in sorted(keys))})"
            if destination:
                # Note: This seems to expect relative path in `destination`,
                #       turns it into absolute and back into relative.
                #       Double-check where `destination` is used and remove
                #       resolution:
                dest = (self.git.root / destination).relative_to(self.git.root)
            if dest and dest.name == self.ANCHOR_FILE:
                dest = dest.parent

            # the `msg_dummy` is the way all automatically generated commit
            # message headers (independently of later adding/shortening of
            # information) begin, for all commands.
            msg_dummy = f"{cmd} [{len(changes_to_record)}]{keys_str}"
            message_subject = self._generate_commit_message_subject(
                msg_dummy, changes_to_record, dest, max_length)

        message_appendix = '\n'.join(map(str, changes_to_record))
        return f"{message_subject}\n\n{message_body}\n\n{message_appendix}"

    @staticmethod
    def _generate_commit_message_subject(msg_dummy: str,
                                         changes: list[Path],
                                         destination: Optional[Path],
                                         max_length: int = 80) -> str:
        """
        Generates a "commit message subject" usable with `git commit`.
        The function lists the paths of `changes` and will shorten the resulting
        string to try to include as much user readable information as possible.

        Parameters
        ----------
        msg_dummy: str
            The first part of commit message subjects generated by Onyo.

        changes: list of paths
            The list of paths modified which should be mentioned in the commit
            message subject.

        destination: path
            Destination for assets/directories when the commit contains `mv`s.

        max_length: int
            Limit the length of the generated message to `max_length` if
            possible.

        Returns
        -------
        str
            A commit message subject to use with `git commit`.
        """

        # long message: full paths (relative to repo-root)
        paths_str = ','.join([f"'{x}'" for x in changes])
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination}'"

        if len(msg) < max_length:
            return msg

        # medium message: highest level (e.g. dir or asset name)
        paths = [x.name for x in changes]
        paths_str = ','.join(["'{}'".format(x) for x in paths])
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination.relative_to(destination.parent)}'"

        if len(msg) < max_length:
            return msg

        # short message: "type" of devices in summary (e.g.  "laptop (2)")
        paths = [x.name.split('_')[0] for x in changes]
        paths_str = ','.join(sorted(["'{} ({})'".format(x, paths.count(x))
                                     for x in set(paths)]))
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination.relative_to(destination.parent)}'"

        # return the shortest possible version of the commit message as fallback
        return msg

    @property
    def asset_paths(self) -> list[Path]:
        """
        Get a `set` containing the absolute `Path`s of all assets of a
        repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `OnyoRepo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `OnyoRepo.clear_caches()`.
        """
        if self._asset_paths is None:
            self._asset_paths = self.get_asset_paths()
        return self._asset_paths

    def is_valid_onyo_repo(self) -> bool:
        """
        Assert whether this is a properly set up onyo repository and has a fully
        populated `.onyo/` directory.

        Returns
        -------
        boolean
            True when the repository is complete and valid, otherwise False.
        """
        files = ['config',
                 OnyoRepo.ANCHOR_FILE,
                 Path(OnyoRepo.TEMPLATE_DIR) / OnyoRepo.ANCHOR_FILE,
                 Path('validation') / OnyoRepo.ANCHOR_FILE]

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
        """Initialize an Onyo repository at `path`.

        Re-init-ing an existing repository is safe. It will not overwrite
        anything; it will raise an exception.

        Parameters
        ----------
        Path: path
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

        self.git.maybe_init(path)

        # Note: pheewww - No. Installed resource needs to be found differently.
        #       Who the hell is supposed to maintain that? One cannot simply
        #       move this function without changing its implementation.
        skel_dir = Path(Path(__file__).resolve().parent.parent, 'skel')

        # populate .onyo dir
        shutil.copytree(skel_dir, self.dot_onyo)

        # add and commit
        self.git.stage_and_commit(self.dot_onyo,
                                  message='Initialize as an Onyo repository')
        ui.print(f'Initialized Onyo repository in {self.dot_onyo}/')

    def is_onyo_path(self,
                     path: Path) -> bool:
        """
        Determine whether an absolute `path` is used by onyo internally.

        Currently anything underneath `.onyo/` as well as anything named
        `.onyo*` is considered an onyo path.

        Parameters
        ----------
        path
          The path to check for if it is inside the `.onyo/` directory.

        Returns
        -------
        boolean
          True if `path` is inside `.onyo/`, otherwise False.
        """
        # TODO: Should this include anchor files?
        return path == self.dot_onyo or self.dot_onyo in path.parents or \
            path.name.startswith('.onyo')  # see .onyoignore

    def is_inventory_dir(self,
                         path: Path) -> bool:
        # - existing inventory directory
        # - includes repo.root as "root location"  --> is this valid?
        # Note: This currently ignores whether there's tracked content in that
        #       dir
        return self.is_inventory_path(path) and path.is_dir()

    def is_asset_path(self,
                      path: Path) -> bool:
        # TODO: check for .onyoignore
        # TODO: possibly nested assets; hence "asset path", not "asset file"
        # TODO: We are currently ignoring .gitignore w/ underlying globbing
        # TODO: Only account for tracked files!
        return self.is_inventory_path(path) and \
            (path.is_file() or (path / self.ASSET_DIR_FILE).is_file())

    def is_inventory_path(self,
                          path: Path) -> bool:
        # Note: path underneath an inventory location with no regard for
        #       existence of `path` itself. This is still a little ugly, since
        #       is_inventory_dir is amost identical. Trouble comes from root
        #       being an inventory dir. Consider lru_cache for these checks.
        #       Dependency is_inventory_dir vs *_path seems wrong. Things change
        #       when we know the path exists, because in case of a file there's
        #       another restriction (ANCHOR)
        return path.is_relative_to(self.git.root) and \
            not self.git.is_git_path(path) and \
            not self.is_onyo_path(path) and \
            self.ANCHOR_FILE not in path.parts

    def is_asset_dir(self, path: Path) -> bool:
        return self.is_inventory_dir(path) and self.is_asset_path(path)

    def get_template(self,
                     name: Optional[str] = None) -> dict:
        """
        Select and return a template from the directory `.onyo/templates/`.

        Parameters
        ----------
        name: str
            The name of the template to look for. If no name is given, the
            template defined in the config file `.onyo/config` is returned.

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
        if not name:
            name = self.get_config('onyo.new.template')
            if name is None:
                return dict()  # equivalent to previous empty default template
                # TODO: is this sane or do we fail? Not raising seems advantageous,
                #       b/c it allows for generic calls -> no template requested, no problem.
                #       Empty dict can still be used as baseline for assembling the "real" dict.

        # Note: Protect against providing absolute path in `template_name`?
        template_file = self.git.root / self.ONYO_DIR / self.TEMPLATE_DIR / name
        if not template_file.is_file():
            raise ValueError(f"Template {name} does not exist.")
        return yaml_to_dict(template_file)

    def validate_anchors(self) -> bool:
        """
        Check if all dirs (except those in `.onyo/`) contain an .anchor file.

        Returns
        -------
        boolean
            True if all directories contain an `.anchor` file, otherwise False.
        """
        # Note: First line not using protected_paths, because `.anchor` is part
        #       of it. But ultimately, exist vs expected should take the same
        #       subtrees into account. So - not good to code it differently.
        anchors_exist = {x
                         for x in self.git.files
                         if x.name == self.ANCHOR_FILE and
                         not self.is_onyo_path(x)}

        anchors_expected = {x.joinpath(self.ANCHOR_FILE)
                            for x in [self.git.root / f for f in self.git.root.glob('**/')]
                            if self.is_inventory_dir(x) and not x == self.git.root}
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

    def get_asset_paths(self, subtrees: Optional[Iterable[Path]] = None, depth: Optional[int] = None) -> List[Path]:

        # TODO: Adjust docstring
        """
        Check and normalize a list of paths. Select all assets in the
        repository that are relative to the given `paths` descending at most
        `depth` directories. A `depth` of 0 or `None` descends without a limit.
        """
        if depth and depth < 0:
            raise ValueError(f"depth values must be positive, but is {depth}.")

        files = self.git.get_subtrees(subtrees)
        if not subtrees:
            asset_paths = [f for f in files
                           if self.is_asset_path(f) and
                           (len(f.parents) - len(self.git.root.parents) <= depth if depth else True)
                           ]
        else:
            asset_paths = [f for f in files
                           if self.is_asset_path(f) and
                           any([f.is_relative_to(p) and
                                (len(f.parents) - len(p.parents) <= depth if depth else True)
                                for p in subtrees]
                               )
                           ]
        return asset_paths

    def get_asset_content(self, path: Path) -> dict:
        if not self.is_asset_path(path):
            raise ValueError(f"{path} is not an asset path")
        if self.is_asset_dir(path):
            a = yaml_to_dict(path / self.ASSET_DIR_FILE)
            a['is_asset_directory'] = True
        else:
            a = yaml_to_dict(path)
        # Add pseudo-keys:
        a['path'] = path
        return a

    def write_asset_content(self, asset: dict) -> dict:
        path = asset.get('path')
        if not path:
            raise RuntimeError("Trying to write asset to unknown path")
        if self.is_inventory_path(path):
            if asset.get('is_asset_directory', False) and path.name != self.ASSET_DIR_FILE:
                path = path / self.ASSET_DIR_FILE
            # TODO: potential rename, based on config??
            path.open('w').write(dict_to_yaml(asset))
        else:
            raise ValueError(f"{path} is not a valid inventory path")
            # TODO: What?

        # TODO: Potentially return/modify updated (pseudo-keys: last modified, etc.!) asset dict.
        return asset

    def mk_inventory_dirs(self,
                          dirs: Union[Iterable[Path], Path]) -> list[Path]:
        """Create inventory directories `dirs`

        Creates `dirs` including anchor files.

        Raises
        ------
        OnyoProtectedPathError
          if `dirs` contains an invalid path (see
          `OnyoRepo.is_inventory_path()`)

        FileExistsError
          if `dirs` contains a path pointing to an existing file (hence, the
          dir can't be created)

        Returns
        -------
        list of Path
          list of created anchor files (paths to be committed)
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
        anchors = {i / OnyoRepo.ANCHOR_FILE for d in dirs
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
