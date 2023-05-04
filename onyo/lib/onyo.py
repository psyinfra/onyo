import logging
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Optional, Union, Generator, Set

from .filters import Filter

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


class OnyoInvalidRepoError(Exception):
    """Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    """Thrown if path is protected (.anchor, .git/, .onyo/)."""


class Repo:
    """
    """
    def __init__(self, path: Union[Path, str], find_root: bool = False,
                 init: bool = False) -> None:
        """
        Instantiates a `Repo` object with `path` as the root directory.

        If `find_root=True` searches the root of a repository from `path`.

        If `init=True`, the `path` will be initialized as a git repo and a
        `.onyo/` directory will be created.
        Otherwise the validity of the onyo repository is verified, and if the
        path is invalid a `OnyoInvalidRepoError` is raised.
        """
        path = Path(path)

        if init:
            path = path.resolve()
            self._init(path)
        else:
            path = self._find_root(path) if find_root else path.resolve()
            if not Repo._is_onyo_root(path):
                log.error(f"'{path}' is no valid Onyo Repository.")
                raise OnyoInvalidRepoError(f"'{path}' is no valid Onyo Repository.")

        self._opdir: Path = path
        self._root: Path = path
        # caches
        self._assets: Union[set[Path], None] = None
        self._dirs: Union[set[Path], None] = None
        self._files: Union[set[Path], None] = None
        self._templates: Union[set[Path], None] = None

    @property
    def assets(self) -> set[Path]:  # pyre-ignore[11]
        """
        A `set` containing the `Path`s relative to `Repo.root` of all assets of
        an Onyo repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `Repo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `Repo.clear_caches()`.
        """
        if not self._assets:
            self._assets = self._get_assets()

        return self._assets

    @property
    def dirs(self) -> set[Path]:
        """
        A `set` containing the `Path`s relative to `Repo.root` of all directories
        of an Onyo repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `Repo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `Repo.clear_caches()`.
        """
        if not self._dirs:
            self._dirs = self._get_dirs()

        return self._dirs

    @property
    def files(self) -> set[Path]:
        """
        A `set` containing the `Paths` relative to `Repo.root` of all files of an
        Onyo repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `Repo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `Repo.clear_caches()`.
        """
        if not self._files:
            self._files = self._get_files()

        return self._files

    @property
    def files_changed(self) -> set[Path]:
        """
        Returns a `set` containing the `Path`s relative to `Repo.root` of all
        changed files (according to git) of an Onyo repository.
        """
        return self._get_files_changed()

    @property
    def files_staged(self) -> set[Path]:
        """
        Returns a `set` containing the `Path`s relative to `Repo.root` of all
        staged files (according to git) of an Onyo repository.
        """
        return self._get_files_staged()

    @property
    def files_untracked(self) -> set[Path]:
        """
        Returns a `set` containing the `Path`s relative to `Repo.root` of all
        untracked files (according to git) of an Onyo repository
        """
        return self._get_files_untracked()

    @property
    def opdir(self) -> Path:
        """
        Returns the absolute `Path` to the working directory where the
        `Repo` object was instantiated.
        """
        return self._opdir

    @property
    def pseudo_keys(self) -> list[str]:
        return ['type', 'make', 'model', 'serial']

    @property
    def root(self) -> Path:
        """
        Returns the absolute `Path` to the root of the `Repo` where the
        directories `.git/` and `.onyo/` are located.
        """
        return self._root

    @property
    def templates(self) -> set[Path]:
        """
        A `set` containing the `Path`s relative to `Repo.root` of all
        template files of an Onyo repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `Repo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `Repo.clear_caches()`.
        """
        if not self._templates:
            self._templates = self._get_templates()

        return self._templates

    def clear_caches(self, assets: bool = True, dirs: bool = True,
                     files: bool = True, templates: bool = True) -> None:
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
        """
        if assets:
            self._assets = None
        if dirs:
            self._dirs = None
        if files:
            self._files = None
        if templates:
            self._templates = None

    def generate_commit_message(
            self, message: Union[list[str], None] = None, cmd: str = "",
            keys: Union[list[str], None] = None, destination: str = "",
            max_length: int = 80) -> str:
        """
        Generate a commit subject and body suitable for use with git commit.

        If `message` is given, the function uses the first element of it to
        generate a message subject, and the following ones are joined for the
        message body.

        If no `message` is given, generate a default commit message based on
        the other parameters given, and the `files staged` in the repository.
        The paths for the message are shortened if needed, so that the resulting
        message subject does not exceed `MAX_LEN`.

        Adds a list of `changed files` with their path relative to the root of
        the repository to the body of all commit messages.
        """
        message = [] if message is None else message
        keys = [] if keys is None else keys

        message_subject = ""
        message_body = ""
        message_appendix = ""

        # staged files and directories (without ".anchor") in alphabetical order
        staged_changes = [x if not x.name == ".anchor" else x.parent
                          for x in sorted(self.files_staged)]

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
                dest = Path(self.opdir, destination).relative_to(self.root)
            if dest and dest.name == ".anchor":
                dest = dest.parent

            # the `msg_dummy` is the way all automatically generated commit
            # message headers (independently of later adding/shortening of
            # information) begin, for all commands.
            msg_dummy = f"{cmd} [{len(staged_changes)}]{keys_str}"
            message_subject = self._generate_commit_message_subject(
                msg_dummy, staged_changes, dest, max_length)

        message_appendix = '\n'.join(map(str, staged_changes))
        return f"{message_subject}\n\n{message_body}\n\n{message_appendix}"

    @staticmethod
    def _generate_commit_message_subject(
            msg_dummy: str, staged_changes: list[Path],
            destination: Optional[Path], max_length: int = 80) -> str:
        """
        Generates "commit message subject" with the `msg_dummy` and the paths
        from `staged_changes` and `destination`, and shortens the paths if the
        message length exceeds the `MAX_LEN`.
        """

        # long message: full paths (relative to repo-root)
        paths_str = ','.join([f"'{x}'" for x in staged_changes])
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination}'"

        if len(msg) < max_length:
            return msg

        # medium message: highest level (e.g. dir or asset name)
        paths = [x.name for x in staged_changes]
        paths_str = ','.join(["'{}'".format(x) for x in paths])
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination.relative_to(destination.parent)}'"

        if len(msg) < max_length:
            return msg

        # short message: "type" of devices in summary (e.g.  "laptop (2)")
        paths = [x.name.split('_')[0] for x in staged_changes]
        paths_str = ','.join(sorted(["'{} ({})'".format(x, paths.count(x))
                                     for x in set(paths)]))
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination.relative_to(destination.parent)}'"

        # return the shortest possible version of the commit message as fallback
        return msg

    def restore(self) -> None:
        """
        Restore all staged files with uncommitted changes in the repository.
        """
        self._git(['restore', '--source=HEAD', '--staged', '--worktree'] +
                  [str(file) for file in self.files_staged])
        # `Repo.restore()` gets used by all most commands that might change the
        # repository to revert changes, especially when users answer "no" to
        # user dialogs. It might also be used by the API to reset the repository
        # variable after doing some manual changes on files (e.g. with
        # subprocess).
        self.clear_caches(assets=True,  # revert e.g. `onyo set`
                          dirs=True,  # revert e.g. `onyo mkdir`
                          files=True,  # revert anchors of `onyo mkdir`
                          templates=True  # revert `onyo edit` in `.onyo`
                          )

    def _get_assets(self) -> set[Path]:
        """
        Return a set of all assets in the repository.
        """
        from .utils import get_assets
        return get_assets(self)

    def _get_dirs(self) -> set[Path]:
        """
        Return a set of all directories in the repository (except under .git).
        """
        log.debug('Acquiring list of directories')
        dirs = {x.relative_to(self.root) for x in Path(self.root).glob('**/')
                if '.git' not in x.parts and
                not x.samefile(self.root)}

        return dirs

    def _get_files(self) -> set[Path]:
        """
        Return a set of all files in the repository (except under .git).
        """
        log.debug('Acquiring list of files')
        files = {Path(x) for x in self._git(['ls-files', '-z']).split('\0') if x}
        return files

    def _get_files_changed(self) -> set[Path]:
        """
        Return a set of all unstaged changes in the repository.
        """
        log.debug('Acquiring list of changed files')
        changed = {Path(x) for x in self._git(['diff', '-z', '--name-only']).split('\0') if x}
        return changed

    def _get_files_staged(self) -> set[Path]:
        """
        Return a set of all staged changes in the repository.
        """
        log.debug('Acquiring list of staged files')
        staged = {Path(x) for x in self._git(['diff', '--name-only', '-z', '--staged']).split('\0') if x}
        return staged

    def _get_files_untracked(self) -> set[Path]:
        """
        Return a set of all untracked files in the repository.
        """
        log.debug('Acquiring list of untracked files')
        untracked = {Path(x) for x in self._git(['ls-files', '-z', '--others', '--exclude-standard']).split('\0') if x}
        return untracked

    @staticmethod
    def _find_root(directory: Path) -> Path:
        """
        Find and return the root of an Onyo repository (containing `.git/` and
        `.onyo/`) for a given `Path` inside of an existing repository.

        If the `directory` is not inside an existing repository, an error is
        raised.
        """
        root = None

        try:
            ret = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                 cwd=directory, check=True,
                                 capture_output=True, text=True)
            root = Path(ret.stdout.strip()).resolve()
        except (subprocess.CalledProcessError, FileNotFoundError):
            log.error(f"'{directory}' is not a Git repository.")
            raise OnyoInvalidRepoError(f"'{directory}' is not a Git repository.")

        if not Path(root, '.onyo').is_dir():
            log.error(f"'{root}' is not an Onyo repository.")
            raise OnyoInvalidRepoError(f"'{root / '.onyo'}' is missing or not a directory.")
        # TODO: check .onyo/config, etc

        log.debug(f"Onyo repo found at '{root}'")
        return root

    def _get_templates(self) -> set[Path]:
        from .utils import get_templates
        return get_templates(self)

    #
    # HELPERS
    #
    @staticmethod
    def _is_protected_path(path: Union[Path, str]) -> bool:
        """
        Checks whether a path contains protected elements (.anchor, .git, .onyo).
        Returns True if it contains protected elements. Otherwise False.
        """
        from .utils import is_protected_path
        return is_protected_path(path)

    #
    # _git
    #
    def _git(self, args: list[str], *, cwd: Optional[Path] = None, raise_error: bool = True) -> str:
        """
        """
        if cwd is None:
            cwd = self.opdir

        log.debug(f"Running 'git {args}'")
        ret = subprocess.run(["git"] + args,
                             cwd=cwd, check=raise_error,
                             capture_output=True, text=True)

        return ret.stdout

    #
    # ADD
    #
    def add(self, targets: Union[Iterable[Union[Path, str]], Path, str]) -> None:
        """
        Perform ``git add`` to stage files.

        Paths are relative to ``root.opdir``.
        """
        if isinstance(targets, (list, set)):
            tgts = [str(x) for x in targets]
        else:
            tgts = [str(targets)]

        for t in tgts:
            if not Path(self.opdir, t).exists():
                log.error(f"'{t}' does not exist.")
                raise FileNotFoundError(f"'{t}' does not exist.")

        self._git(['add'] + tgts)
        # `Repo.add()` is used by most repo-changing commands, and it might be
        # used often by the API to change the repository, before manually
        # calling clear_cache() or after a file was changed with a subprocess
        # call. To always secure the integrity of the caches, we reset them all.
        self.clear_caches(assets=True,  # e.g. `onyo set` changes asset names
                          dirs=True,  # e.g. `onyo mkdir` adds new dirs
                          files=True,  # e.g. `onyo mkdir` adds new ".anchor"
                          templates=True  # e.g. `onyo edit` in `.onyo/templates`
                          )

    #
    # COMMIT
    #
    def commit(self, *args) -> None:
        """
        Perform a ``git commit``. The first message argument is the title; each
        argument after is a new paragraph. Messages are converted to strings.
        Lists are printed one item per line, also converted to a string.
        """
        if not args:
            raise ValueError('at least one commit message is required')

        messages = []
        for i in args:
            if not i:
                raise ValueError('commit messages cannot be empty')

            messages.append('-m')
            if isinstance(i, (list, set)):
                messages.append('\n'.join(map(str, i)))
            else:
                messages.append(str(i))

        self._git(['commit'] + messages)

    #
    # CONFIG
    #
    def get_config(self, name: str) -> Union[str, None]:
        """
        Get the value for a configuration option specified by `name`.

        git-config is checked following its order of precedence (worktree,
        local, global, system). If the config name is not found, .onyo/config is
        checked.

        Returns a string with the config value on success. None otherwise.
        """
        value = None

        # git-config (with its full stack of locations to check)
        try:
            value = self._git(['config', '--get', name]).strip()
            log.debug(f"git config acquired '{name}': '{value}'")
        except subprocess.CalledProcessError:
            log.debug(f"git config missed '{name}'")
            pass

        # .onyo/config
        if not value:
            dot_onyo_config = str(Path(self.root, '.onyo/config'))
            try:
                value = self._git(['config', '--file', dot_onyo_config, '--get', name]).strip()
                log.debug(f"onyo config acquired '{name}': '{value}'")
            except subprocess.CalledProcessError:
                log.debug(f"onyo config missed '{name}'")
                pass

        return value

    def set_config(self, name: str, value: str, location: str = 'onyo') -> bool:
        """
        Set the `name` configuration option to `value`. The local is `onyo` by
        default. Other git config locations are: `system`, `global`, `local`,
        and `worktree`.

        Returns True on success. Raises an exception otherwise.
        """
        location_options = {
            'onyo': ['--file', str(Path(self.root, '.onyo/config'))],
            'system': ['--system'],
            'global': ['--global'],
            'local': ['--local'],
            'worktree': ['--worktree']
        }
        location_arg = []

        try:
            location_arg = location_options[location]
        except KeyError:
            raise ValueError("Invalid config location requested. Valid options are: {}".format(', '.join(location_options.keys())))

        # git-config (with its full stack of locations to check)
        self._git(['config'] + location_arg + [name, value]).strip()
        log.debug(f"'config for '{location}' set '{name}': '{value}'")

        return True

    #
    # FSCK
    #
    def fsck(self, tests: Optional[list[str]] = None) -> None:
        """
        Run a suite of checks to verify the integrity and validity of an Onyo
        repository and its contents.

        By default, the following tests will be performed:

        - "clean-tree": verifies that the git tree is clean ---that there are
          no changed (staged or unstaged) nor untracked files.
        - "anchors": verifies that all folders (outside of .onyo) have an
          .anchor file
        - "asset-unique": verifies that all asset names are unique
        - "asset-yaml": loads each assets and checks if it's valid YAML
        - "asset-validity": loads each asset and validates the contents against
          the validation rulesets defined in ``.onyo/validation/``.
        - "pseudo-keys": verifies that assets do not contain pseudo-key names
        """
        from .command_utils import fsck as utils_fsck
        utils_fsck(self, tests)

    def _fsck_anchors(self) -> bool:
        """
        Check if all dirs (except those in .onyo) contain an .anchor file.
        Returns True or False.
        """
        from .command_utils import fsck_anchors
        return fsck_anchors(self)

    def _fsck_clean_tree(self) -> bool:
        """
        Check if the working tree for git is clean. Returns True or False.
        """
        from .command_utils import fsck_clean_tree
        return fsck_clean_tree(self)

    def _fsck_pseudo_keys(self) -> bool:
        """
        Check that no asset contains any pseudo-key names.
        """
        from .command_utils import fsck_pseudo_keys
        return fsck_pseudo_keys(self)

    def _fsck_unique_assets(self) -> bool:
        """Check if all asset files have unique names."""
        from .command_utils import fsck_unique_assets
        return fsck_unique_assets(self)

    def _fsck_validation(self) -> bool:
        """
        Check if all assets pass validation. Returns True or False.
        """
        from .command_utils import fsck_validation
        return fsck_validation(self)

    def _fsck_yaml(self) -> bool:
        """
        Check if all assets have valid YAML. Returns True or False.
        """
        from .command_utils import fsck_yaml
        return fsck_yaml(self)

    #
    # INIT
    #
    def _init(self, directory: Path) -> None:
        """
        Initialize an Onyo repository. The directory will be initialized as a
        git repository (if it is not one already), ``.onyo/`` directory created
        (containing default config files, templates, etc), and everything
        committed.

        Re-init-ing an existing repository is safe. It will not overwrite
        anything; it will raise an exception.
        """
        from .command_utils import init_onyo
        return init_onyo(self, directory)

    @staticmethod
    def _is_onyo_root(directory: Path) -> bool:
        """
        Assert whether a directory is the root of a repository and has a fully
        populated `.onyo/` directory.
        """
        dot_onyo = Path(directory, '.onyo')

        if not dot_onyo.is_dir() or \
                not Path(dot_onyo, "templates").is_dir() or \
                not Path(dot_onyo, "validation").is_dir() or \
                not Path(dot_onyo, "config").is_file() or \
                not Path(dot_onyo, ".anchor").is_file() or \
                not Path(dot_onyo, "templates/.anchor").is_file() or \
                not Path(dot_onyo, "validation/.anchor").is_file():
            return False  # noqa: E111, E117

        if subprocess.run(["git", "rev-parse"], cwd=directory,
                          stdout=subprocess.DEVNULL).returncode != 0:
            return False

        return True

    @staticmethod
    def _init_sanitize(directory: Union[Path, str]) -> Path:
        """
        Check the target path for viability as an init target.

        Returns an absolute Path on success.
        """
        from .command_utils import init_sanitize
        return init_sanitize(directory)

    #
    # MKDIR
    #
    def mkdir(self, directories: Union[Iterable[Union[Path, str]], Path, str]) -> None:
        """
        Create ``directory``\\(s). Intermediate directories will be created as
        needed (i.e. parent and child directories can be created in one call).

        An empty ``.anchor`` file is added to each directory, to ensure that
        git tracks it even when empty.

        If a directory already exists, or the path is protected, an exception
        will be raised. All checks are performed before creating directories.
        """
        from .command_utils import mk_onyo_dir
        mk_onyo_dir(self, directories)

    def _mkdir_sanitize(self, dirs: Iterable[Union[Path, str]]) -> set[Path]:
        """
        Check and normalize a list of directories.

        Returns a list of absolute Paths.
        """
        from .command_utils import mkdir_sanitize
        return mkdir_sanitize(self, dirs)

    #
    # MV
    #
    def mv(
            self, sources: Union[Iterable[Union[Path, str]], Path, str],
            destination: Union[Path, str],
            dryrun: bool = False) -> list[tuple[str, str]]:
        """
        Move ``source``\\(s) (assets or directories) to the ``destination``
        directory, or rename a ``source`` directory to ``destination``.

        Files cannot be renamed using ``mv()``. To do so, use ``set()``.
        """
        from .command_utils import mv
        return mv(self, sources, destination, dryrun)

    def _mv_move_mode(self, sources: list[Union[Path, str]], destination: Union[Path, str]) -> bool:
        """
        `mv()` can be used to either move or rename a file/directory. The mode
        is not explicitly declared by the user, and must be inferred from the
        arguments.

        Returns True if "move" mode and False if not.
        """
        from .command_utils import mv_move_mode
        return mv_move_mode(self, sources, destination)

    def _mv_rename_mode(self, sources: list[Union[Path, str]], destination: Union[Path, str]) -> bool:
        """
        Returns True if "rename" mode and False if not.

        The inverse of `move_mode()`. See its docstring for more information.
        """
        from .command_utils import mv_rename_mode
        return mv_rename_mode(self, sources, destination)

    def _mv_sanitize_destination(self, sources: list[Union[Path, str]], destination: Union[Path, str]) -> Path:
        """
        Perform a sanity check on the destination. This includes protected
        paths, conflicts, and other pathological scenarios.

        Returns an absolute Path on success.
        """
        from .command_utils import mv_sanitize_destination
        return mv_sanitize_destination(self, sources, destination)

    def _mv_sanitize_sources(self, sources: list[Union[Path, str]]) -> list[Path]:
        """
        Check and normalize a list of paths. If any do not exist, or are
        protected paths (.anchor, .git, .onyo), then an exception will be
        raised.

        Returns a list of absolute Paths.
        """
        from .command_utils import mv_sanitize_sources
        return mv_sanitize_sources(self, sources)

    #
    # NEW
    #
    def generate_faux_serials(self, length: int = 6, num: int = 1) -> set[str]:
        """
        Generate a unique faux serial and verify that it is not used by any
        other asset in the repository. The length of the faux serial must be 4
        or greater.

        Returns a set of unique faux serials.
        """
        from .command_utils import generate_faux_serials
        return generate_faux_serials(self, length, num)

    def get_template(self, template_name: Union[Path, str, None] = None) -> Path:
        """
        Select the template to use. If no template name is given, use the
        template from the repository config file `.onyo/config`.

        Returns the template path on success, or exits with error.
        """
        from .command_utils import get_template
        return get_template(self, template_name)

    def valid_asset_path_and_name_available(self, asset: Path, new_assets: list[Path]) -> None:
        """
        Test for an assets path and name if it can be used to create a new asset.
        """
        from .command_utils import valid_asset_path_and_name_available
        valid_asset_path_and_name_available(self, asset, new_assets)

    def valid_name(self, asset: Union[Path, str]) -> bool:
        """
        Verify that an asset name complies with the name scheme:
        <type>_<make>_<model>.<serial>
        Where the fields type, make, and model do not allow '.' or '_', serial
        permits all characters, and no field can be empty.

        Returns True for valid asset names, and False if invalid.
        """
        from .command_utils import valid_name
        return valid_name(asset)

    #
    # SET
    #
    def set(self, paths: Iterable[Union[Path, str]],
            values: Dict[str, Union[str, int, float]], dryrun: bool,
            rename: bool, depth: Union[int]) -> str:
        """
        Set values for a list of assets (or directories), or rename assets
        through updating their name fields.

        A flag enable to limit the depth of recursion for setting values in
        directories.
        """
        from .command_utils import set_assets
        return set_assets(self, paths, values, dryrun, rename, depth)

    def _diff_changes(self) -> str:
        """
        Return a diff of all uncommitted changes. The format is a simplified
        version of `git diff`.
        """
        diff = self._git(['--no-pager', 'diff', 'HEAD']).splitlines()
        diff = [line.strip().replace("+++ b/", "\n").replace("+++ /dev/null", "\n")
                for line in diff if len(line) > 0 and line[0] in ['+', '-'] and not
                line[0:4] == '--- ' or "rename" in line]

        return "\n".join(diff).strip()

    @staticmethod
    def _read_asset(asset: Path) -> Dict[str, Union[str, int, float]]:
        """
        Read and return the contents of an asset as a dictionary.
        """
        from .utils import read_asset
        return read_asset(asset)

    def _get_assets_by_path(
            self, paths: Iterable[Union[Path, str]],
            depth: Union[int, None]) -> list[Path]:
        """
        Check and normalize a list of paths. Select all assets in the
        repository that are relative to the given `paths` descending at most
        `depth` directories. A `depth` of 0 descends without a limit.
        """
        from .utils import get_assets_by_path
        return get_assets_by_path(self, paths=paths, depth=depth)

    def _update_names(self, assets: list[Path],
                      name_values: Dict[str, Union[float, int, str]]) -> None:
        """
        Set the pseudo key fields of an assets name (rename an asset file) from
        values of a dictionary and test that the new name is valid and
        available.
        """
        from .command_utils import update_names
        update_names(self, assets, name_values)

    @staticmethod
    def _write_asset(asset: Path,
                     contents: Dict[str, Union[float, int, str]]) -> None:
        """
        Write contents into an asset file.
        """
        from .utils import write_asset
        write_asset(asset, contents)

    #
    # RM
    #
    def rm(self, paths: Union[Iterable[Union[Path, str]], Path, str], dryrun: bool = False) -> list[str]:
        """
        Delete ``asset``\\(s) and ``directory``\\(s).
        """
        from .command_utils import rm
        return rm(self, paths, dryrun)

    def _rm_sanitize(self, paths: Iterable[Union[Path, str]]) -> list[Path]:
        """
        Check and normalize a list of paths.

        Returns a list of absolute Paths.
        """
        from .command_utils import rm_sanitize
        return rm_sanitize(self, paths)

    #
    # UNSET
    #
    def unset(self, paths: Iterable[Union[Path, str]], keys: list[str],
              dryrun: bool, quiet: bool, depth: Union[int]) -> str:

        from .command_utils import unset
        return unset(self, paths, keys, dryrun, quiet, depth)

    def get(
            self, keys: Set[str], paths: Set[Path],
            depth: Union[int, None] = None,
            filters: Union[list[Filter], None] = None) -> Generator:
        """
        Get keys from assets matching paths and filters.
        """
        from .command_utils import get
        return get(self, keys, paths, depth, filters)
