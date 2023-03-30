import logging
import random
import re
import shutil
import string
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

logging.basicConfig()
log = logging.getLogger('onyo')


class OnyoInvalidRepoError(Exception):
    """Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    """Thrown if path is protected (.anchor, .git/, .onyo/)."""


class Repo:
    """
    """
    def __init__(self, path: Union[Path, str], init: bool = False) -> None:
        if init:
            self._init(path)

        self._opdir = Path(path).resolve()
        self._root = self._get_root()
        # caches
        self._assets = None
        self._dirs = None
        self._files = None
        self._templates = None

    @property
    def assets(self) -> set[Path]:  # pyre-ignore[11]
        if not self._assets:
            self._assets = self._get_assets()

        return self._assets

    @property
    def dirs(self) -> set[Path]:
        if not self._dirs:
            self._dirs = self._get_dirs()

        return self._dirs

    @property
    def files(self) -> set[Path]:
        if not self._files:
            self._files = self._get_files()

        return self._files

    @property
    def files_changed(self) -> set[Path]:
        return self._get_files_changed()

    @property
    def files_staged(self) -> set[Path]:
        return self._get_files_staged()

    @property
    def files_untracked(self) -> set[Path]:
        return self._get_files_untracked()

    @property
    def opdir(self) -> Path:
        return self._opdir

    @property
    def root(self) -> Path:
        return self._root

    @property
    def templates(self) -> set[Path]:
        if not self._templates:
            self._templates = self._get_templates()

        return self._templates

    def clear_caches(self) -> None:
        self._assets = None
        self._dirs = None
        self._files = None
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
            message_body = self._n_join([x[0] for x in message[1:]])
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

        message_appendix = self._n_join([str(x) for x in staged_changes])
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

    def _get_assets(self) -> set[Path]:
        """
        Return a set of all assets in the repository.
        """
        assets = {x for x in self.files if not self._is_protected_path(x)}

        # TODO: make if asset-style name (i.e. README won't match)
        # TODO: check for .onyoignore

        return assets

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

    def _get_root(self) -> Path:
        """
        """
        try:
            root = self._git(['rev-parse', '--show-toplevel'], cwd=self._opdir).strip()
        except subprocess.CalledProcessError:
            log.error(f"'{self._opdir}' is not a Git repository.")
            raise OnyoInvalidRepoError(f"'{self._opdir}' is not a Git repository.")

        root = Path(root)
        if not Path(root, '.onyo').is_dir():
            log.error(f"'{root}' is not an Onyo repository.")
            raise OnyoInvalidRepoError(f"'{self._opdir}' is not an Onyo repository.")

        # TODO: check .onyo/config, etc

        log.debug(f"Onyo repo found at '{root}'")
        return root

    def _get_templates(self) -> set[Path]:
        templates = {Path(file) for file in Path(self.root, ".onyo", "templates").glob('*') if
                     Path(file).is_file() and not Path(file).name == ".anchor"}

        return templates

    #
    # HELPERS
    #
    @staticmethod
    def _is_protected_path(path: Union[Path, str]) -> bool:
        """
        Checks whether a path contains protected elements (.anchor, .git, .onyo).
        Returns True if it contains protected elements. Otherwise False.
        """
        full_path = Path(path).resolve()

        # protected paths
        for p in full_path.parts:
            if p in ['.anchor', '.git', '.onyo']:
                return True

        return False

    @staticmethod
    def _n_join(to_join: Iterable) -> str:
        """
        Convert an Iterable's contents to strings and join with newlines.
        """
        return '\n'.join([str(x) for x in to_join])

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
                messages.append(self._n_join(i))
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
        all_tests = {
            "clean-tree": self._fsck_clean_tree,
            "anchors": self._fsck_anchors,
            "asset-unique": self._fsck_unique_assets,
            "asset-yaml": self._fsck_yaml,
            "asset-validity": self._fsck_validation,
            "pseudo-keys": self._fsck_pseudo_keys,
        }
        if tests:
            # only known tests are accepted
            if [x for x in tests if x not in all_tests.keys()]:
                raise ValueError("Invalid test requested. Valid tests are: {}".format(', '.join(all_tests.keys())))
        else:
            tests = list(all_tests.keys())

        # run the selected tests
        for key in tests:
            # TODO: these should be INFO
            log.debug(f"'{key}' starting")

            if not all_tests[key]():
                log.debug(f"'{key}' failed")
                raise OnyoInvalidRepoError(f"'{self._opdir}' failed fsck test '{key}'")

            log.debug(f"'{key}' succeeded")

    def _fsck_anchors(self) -> bool:
        """
        Check if all dirs (except those in .onyo) contain an .anchor file.
        Returns True or False.
        """
        anchors_exist = {x for x in self.files if x.name == '.anchor' and '.onyo' not in x.parts}
        anchors_expected = {x.joinpath('.anchor') for x in self.dirs
                            if not self._is_protected_path(x)}
        difference = anchors_expected.difference(anchors_exist)

        if difference:
            log.warning('The following .anchor files are missing:\n' +
                        self._n_join(difference))
            log.warning("Likely 'mkdir' was used to create the directory. Use 'onyo mkdir' instead.")
            # TODO: Prompt the user if they want Onyo to fix it.

            return False

        return True

    def _fsck_clean_tree(self) -> bool:
        """
        Check if the working tree for git is clean. Returns True or False.
        """
        changed = {str(x) for x in self.files_changed}
        staged = {str(x) for x in self.files_staged}
        untracked = {str(x) for x in self.files_untracked}

        if changed or staged or untracked:
            log.error('The working tree is not clean.')

            if changed:
                log.error('Changes not staged for commit:\n' +
                          self._n_join(changed))

            if staged:
                log.error('Changes to be committed:\n' +
                          self._n_join(staged))

            if untracked:
                log.error('Untracked files:\n' +
                          self._n_join(untracked))

            log.error('Please commit all changes or add untracked files to .gitignore')

            return False

        return True

    def _fsck_pseudo_keys(self) -> bool:
        """
        Check that no asset contains any pseudo-key names.
        """
        assets_failed = {}
        pseudo_keys = ["type", "make", "model", "serial"]

        for asset in self.assets:
            violation_list = [x for x in pseudo_keys if x in self._read_asset(asset)]
            if violation_list:
                assets_failed[asset] = violation_list

        if assets_failed:
            log.error(f"Pseudo keys ({', '.join(pseudo_keys)}) are reserved for asset names, and are not allowed in asset files. The following assets contain pseudo keys:\n" +
                      self._n_join([f'{asset}: ' +
                                    ', '.join([k for k in assets_failed[asset]])
                                    for asset in assets_failed]))

            return False

        return True

    def _fsck_unique_assets(self) -> bool:
        """
        Check if all files have unique names. Returns True or False.
        """
        names = {}
        for f in self.assets:
            try:
                names[f.name].append(f)
            except KeyError:
                names[f.name] = [f]

        if len(self.assets) != len(names):
            log.error('The following file names are not unique:\n' +
                      '\n'.join([str(y) for x in names for y in names[x]
                                 if len(names[x]) > 1]))

            return False

        return True

    def _fsck_validation(self) -> bool:
        """
        Check if all assets pass validation. Returns True or False.
        """
        invalid = {}
        for asset in self.assets:
            # TODO: validate assets
            pass

        if invalid:
            log.error('The contents of the following files fail validation:\n' +
                      '\n'.join([f'{x}\n{invalid[x]}' for x in invalid]))

            return False

        return True

    def _fsck_yaml(self) -> bool:
        """
        Check if all assets have valid YAML. Returns True or False.
        """
        invalid_yaml = []

        for asset in self.assets:
            # TODO: use valid_yaml()
            try:
                YAML(typ='rt').load(Path(self.root, asset))
            except scanner.ScannerError:
                invalid_yaml.append(str(asset))

        if invalid_yaml:
            log.error('The following files fail YAML validation:\n' +
                      self._n_join(invalid_yaml))

            return False

        return True

    #
    # INIT
    #
    def _init(self, directory: Union[Path, str]) -> None:
        """
        Initialize an Onyo repository. The directory will be initialized as a
        git repository (if it is not one already), ``.onyo/`` directory created
        (containing default config files, templates, etc), and everything
        committed.

        Re-init-ing an existing repository is safe. It will not overwrite
        anything; it will raise an exception.
        """
        target_dir = self._init_sanitize(directory)
        skel_dir = Path(Path(__file__).resolve().parent.parent, 'skel')
        dot_onyo = Path(target_dir, '.onyo')

        # create target if it doesn't already exist
        target_dir.mkdir(exist_ok=True)

        # git init (if needed)
        if Path(target_dir, '.git').exists():
            log.info(f"'{target_dir}' is already a git repository.")
        else:
            ret = self._git(['init'], cwd=target_dir)
            log.info(ret.strip())

        # populate .onyo dir
        shutil.copytree(skel_dir, dot_onyo)

        # add and commit
        self._git(['add', '.onyo/'], cwd=target_dir)
        self._git(['commit', '-m', 'Initialize as an Onyo repository'], cwd=target_dir)

        log.info(f'Initialized Onyo repository in {dot_onyo}/')

    @staticmethod
    def _init_sanitize(directory: Union[Path, str]) -> Path:
        """
        Check the target path for viability as an init target.

        Returns an absolute Path on success.
        """
        full_path = Path(directory).resolve()

        # target must be a directory
        if full_path.exists() and not full_path.is_dir():
            log.error(f"'{full_path}' exists but is not a directory.")
            raise FileExistsError(f"'{full_path}' exists but is not a directory.")

        # parent must exist
        if not full_path.parent.exists():
            log.error(f"'{full_path.parent}' does not exist.")
            raise FileNotFoundError(f"'{full_path.parent}' does not exist.")

        # cannot already be an .onyo repo
        dot_onyo = Path(full_path, '.onyo')
        if dot_onyo.exists():
            log.error(f"'{dot_onyo}' already exists.")
            raise FileExistsError(f"'{dot_onyo}' already exists.")

        return full_path

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
        if not isinstance(directories, (list, set)):
            directories = [directories]

        dirs = self._mkdir_sanitize(directories)
        # make dirs
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # anchors
        anchors = {Path(i, '.anchor') for d in dirs
                   for i in [d] + list(d.parents)
                   if i.is_relative_to(self.root) and
                   not i.samefile(self.root)}
        for a in anchors:
            a.touch(exist_ok=True)

        self.add(anchors)

    def _mkdir_sanitize(self, dirs: Iterable[Union[Path, str]]) -> set[Path]:
        """
        Check and normalize a list of directories.

        Returns a list of absolute Paths.
        """
        error_exist = []
        error_path_protected = []
        dirs_to_create = set()
        # TODO: the set() neatly avoids creating the same dir twice. Intentional?

        for d in dirs:
            full_dir = Path(self.opdir, d).resolve()

            # check if it exists
            if full_dir.exists():
                error_exist.append(d)
                continue

            # protected paths
            if self._is_protected_path(full_dir):
                error_path_protected.append(d)
                continue

            dirs_to_create.add(full_dir)

        # errors
        if error_exist:
            log.error('The following paths already exist:\n' +
                      self._n_join(error_exist) + '\n' +
                      'No directories were created.')
            raise FileExistsError('The following paths already exist:\n' +
                                  self._n_join(error_exist))

        if error_path_protected:
            log.error('The following paths are protected by onyo:\n' +
                      self._n_join(error_path_protected) + '\n' +
                      'No directories were created.')
            raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                         self._n_join(error_path_protected))

        return dirs_to_create

    #
    # MV
    #
    def mv(self, sources: Union[Iterable[Union[Path, str]], Path, str], destination: Union[Path, str], dryrun: bool = False) -> list[tuple[str, str]]:
        """
        Move ``source``\\(s) (assets or directories) to the ``destination``
        directory, or rename a ``source`` directory to ``destination``.

        Files cannot be renamed using ``mv()``. To do so, use ``set()``.
        """
        if not isinstance(sources, (list, set)):
            sources = [sources]
        elif not isinstance(sources, list):
            sources = list(sources)

        # sanitize and validate arguments
        src_paths = self._mv_sanitize_sources(sources)
        dest_path = self._mv_sanitize_destination(sources, destination)

        if dryrun:
            ret = self._git(['mv', '--dry-run'] + [str(x) for x in src_paths] + [str(dest_path)])
        else:
            ret = self._git(['mv'] + [str(x) for x in src_paths] + [str(dest_path)])

        # TODO: change this to info
        log.debug('The following will be moved:\n' +
                  '\n'.join([str(x.relative_to(self.opdir)) for x in src_paths]))

        # return a list of mv-ed assets
        # TODO: is this relative to opdir or root? (should be opdir)
        return [r for r in re.findall('Renaming (.*) to (.*)', ret)]

    def _mv_move_mode(self, sources: list[Union[Path, str]], destination: Union[Path, str]) -> bool:
        """
        `mv()` can be used to either move or rename a file/directory. The mode
        is not explicitly declared by the user, and must be inferred from the
        arguments.

        Returns True if "move" mode and False if not.
        """
        # can only rename one item
        if len(sources) > 1:
            return True

        if Path(self.opdir, destination).resolve().is_dir():
            return True

        # explicitly restating the source name at the destination is a move
        if Path(sources[0]).name == Path(destination).name and not Path(self.opdir, destination).resolve().exists():
            return True

        return False

    def _mv_rename_mode(self, sources: list[Union[Path, str]], destination: Union[Path, str]) -> bool:
        """
        Returns True if "rename" mode and False if not.

        The inverse of `move_mode()`. See its docstring for more information.
        """
        return not self._mv_move_mode(sources, destination)

    def _mv_sanitize_destination(self, sources: list[Union[Path, str]], destination: Union[Path, str]) -> Path:
        """
        Perform a sanity check on the destination. This includes protected
        paths, conflicts, and other pathological scenarios.

        Returns an absolute Path on success.
        """
        error_path_conflict = []
        dest_path = Path(self.opdir, destination).resolve()

        """
        Common checks
        """
        # protected paths
        if self._is_protected_path(dest_path):
            log.error('The following paths are protected by onyo:\n' +
                      f'{dest_path}\n' +
                      'Nothing was moved.')
            raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                         f'{dest_path}')

        # destination cannot be a file
        if dest_path.is_file():
            # This intentionally raises FileExistsError rather than NotADirectoryError.
            # It reduces the number of different exceptions that can be raised
            # by `mv()`, and keeps the exception type unified with other similar
            # situations (such as implicit conflict with the destination).
            log.error(f"The destination '{dest_path}' cannot be a file.\n" +
                      'Nothing was moved.')
            raise FileExistsError(f"The destination '{dest_path}' cannot be a file.\n" +
                                  'Nothing was moved.')

        # check for conflicts and general insanity
        for src in sources:
            src_path = Path(self.opdir, src).resolve()
            new_path = Path(dest_path, src_path.name).resolve()
            if not dest_path.exists:
                new_path = Path(dest_path).resolve()

            # cannot rename/move into self
            if src_path in new_path.parents:
                log.error(f"Cannot move '{src}' into itself.\n" +
                          "Nothing was moved.")
                raise ValueError(f"Cannot move '{src}' into itself.\n" +
                                 "Nothing was moved.")

            # target paths cannot already exist
            if new_path.exists():
                error_path_conflict.append(new_path)
                continue

        if error_path_conflict:
            log.error('The following destinations exist and would conflict:\n' +
                      self._n_join(error_path_conflict) + '\n' +
                      'Nothing was moved.')
            raise FileExistsError('The following destination paths exist and would conflict.\n' +
                                  self._n_join(error_path_conflict) + '\n' +
                                  'Nothing was moved.')

        # parent must exist
        if not dest_path.parent.exists():
            log.error(f"The destination '{dest_path.parent}' does not exist.\n" +
                      "Nothing was moved.")
            raise FileNotFoundError(f"The destination '{dest_path.parent}' does not exist.\n" +
                                    "Nothing was moved.")

        if self._mv_rename_mode(sources, destination):
            """
            Rename mode checks
            """
            log.debug("'mv' in rename mode")
            # renaming files is not allowed
            src_path = Path(self.opdir, sources[0]).resolve()
            if src_path.is_file() and src_path.name != dest_path.name:
                log.error(f"Cannot rename asset '{src_path.name}' to '{dest_path.name}'.\n" +
                          "Use 'set()' to rename assets.\n" +
                          "Nothing was moved.")
                raise ValueError(f"Cannot rename asset '{src_path.name}' to '{dest_path.name}'.\n" +
                                 "Use 'set()' to rename assets.\n" +
                                 "Nothing was moved.")

            # target cannot already exist
            if dest_path.exists():
                log.error(f"The destination '{dest_path}' exists and would conflict.\n" +
                          "Nothing was moved.")
                raise FileExistsError(f"The destination '{dest_path}' exists and would conflict.\n" +
                                      "Nothing was moved.")
        else:
            """
            Move mode checks
            """
            log.debug("'mv' in move mode")

            # check if same name is specified as the destination
            # (e.g. rename to same name is a move)
            if src_path.name != dest_path.name:
                # dest must exist
                if not dest_path.exists():
                    log.error(f"The destination '{destination}' does not exist.\n" +
                              "Nothing was moved.")
                    raise FileNotFoundError(f"The destination '{destination}' does not exist.\n" +
                                            "Nothing was moved.")

            # cannot move onto self
            if src_path.is_file() and dest_path.is_file() and src_path.samefile(dest_path):
                log.error(f"Cannot move '{src}' onto itself.\n" +
                          "Nothing was moved.")
                raise FileExistsError(f"Cannot move '{src}' onto itself.\n" +
                                      "Nothing was moved.")

        return dest_path

    def _mv_sanitize_sources(self, sources: list[Union[Path, str]]) -> list[Path]:
        """
        Check and normalize a list of paths. If any do not exist, or are
        protected paths (.anchor, .git, .onyo), then an exception will be
        raised.

        Returns a list of absolute Paths.
        """
        paths_to_mv = []
        error_path_absent = []
        error_path_protected = []

        # validate sources
        for src in sources:
            full_path = Path(self.opdir, src).resolve()

            # paths must exist
            if not full_path.exists():
                error_path_absent.append(src)
                continue

            # protected paths
            if self._is_protected_path(full_path):
                error_path_protected.append(src)
                continue

            paths_to_mv.append(full_path)

        if error_path_absent:
            log.error('The following source paths do not exist:\n' +
                      self._n_join(error_path_absent) + '\n' +
                      'Nothing was moved.')
            raise FileNotFoundError('The following paths do not exist:\n' +
                                    self._n_join(error_path_absent))

        if error_path_protected:
            log.error('The following paths are protected by onyo:\n' +
                      self._n_join(error_path_protected) + '\n' +
                      'Nothing was moved.')
            raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                         self._n_join(error_path_protected))

        return paths_to_mv

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
        if length < 4:
            # 62^4 is ~14.7 million combinations. Which is the lowest acceptable
            # risk of collisions between independent checkouts of a repo.
            raise ValueError('The length of faux serial numbers must be >= 4.')

        if num < 1:
            raise ValueError('The length of faux serial numbers must be >= 1.')

        alphanum = string.ascii_letters + string.digits
        faux_serials = set()
        repo_faux_serials = {str(x.name).split('faux')[-1] for x in self.assets}

        while len(faux_serials) < num:
            serial = ''.join(random.choices(alphanum, k=length))
            if serial not in repo_faux_serials:
                faux_serials.add(f'faux{serial}')

        return faux_serials

    def get_template(self, template_name: Union[Path, str, None] = None) -> Path:
        """
        Select the template to use. If no template name is given, use the
        template from the repository config file `.onyo/config`.

        Returns the template path on success, or exits with error.
        """
        if not template_name:
            template_name = self.get_config('onyo.new.template')
            if template_name is None:
                log.error("Either --template must be given or 'onyo.new.template' must be set.")
                raise ValueError("Either --template must be given or 'onyo.new.template' must be set.")

        template_name = Path(template_name)
        for template in self.templates:
            if template.name == template_name.name:
                return template
            elif template_name.is_file() and template.samefile(template_name):
                return template

        log.error(f"Template {template_name} does not exist.")
        raise ValueError(f"Template {template_name} does not exist.")

    def valid_asset_path_and_name_available(self, asset: Path, new_assets: list[Path]) -> None:
        """
        Test for an assets path and name if it can be used to create a new asset.
        """
        if not self.valid_name(asset):
            log.error(f"'{asset}' is not a valid asset name.")
            raise ValueError(f"'{asset}' is not a valid asset name.")
        if file := [file for file in self.assets if asset.name == file.name]:
            log.error(f"Filename '{asset.name}' already exists as '{file[0]}'.")
            raise ValueError(f"Filename '{asset.name}' already exists as '{file[0]}'.")
        elif file := [file for file in new_assets if asset.name == file.name]:
            log.error(f"Input contains multiple '{file[0].name}'")
            raise ValueError(f"Input contains multiple '{file[0].name}'")
        if self._is_protected_path(asset):
            log.error(f"The path is protected by onyo: '{asset}'")
            raise ValueError(f"Input contains multiple '{file[0].name}'")

    def valid_name(self, asset: Union[Path, str]) -> bool:
        """
        Verify that an asset name complies with the name scheme:
        <type>_<make>_<model>.<serial>
        Where the fields type, make, and model do not allow '.' or '_', serial
        permits all characters, and no field can be empty.

        Returns True for valid asset names, and False if invalid.
        """
        asset = Path(asset)

        try:
            re.findall(r'(^[^._]+?)_([^._]+?)_([^._]+?)\.(.+)', asset.name)[0]
        except (ValueError, IndexError):
            log.info(f"'{asset.name}' must be in the format '<type>_<make>_<model>.<serial>'")
            return False

        return True

    #
    # SET
    #
    def set(self, paths: Iterable[Union[Path, str]], values: dict, dryrun: bool,
            rename: bool, depth: Union[int]) -> str:
        """
        Set values for a list of assets (or directories), or rename assets
        through updating their name fields.

        A flag enable to limit the depth of recursion for setting values in
        directories.
        """
        assets_to_set = self._set_sanitize(paths, depth)

        content_values = dict((field, values[field]) for field in values.keys() if field not in ["type", "make", "model", "serial"])
        name_values = dict((field, values[field]) for field in values.keys() if field in ["type", "make", "model", "serial"])

        if name_values and not rename:
            log.error("Can't change pseudo keys without --rename.")
            raise ValueError("Can't change pseudo keys without --rename.")

        if content_values:
            for asset in assets_to_set:
                contents = self._read_asset(asset)
                contents.update(content_values)
                self._write_asset(asset, contents)
                self.add(asset)

        if name_values:
            try:
                self._update_names(assets_to_set, name_values)
                self.clear_caches()
            except ValueError as e:
                self.clear_caches()
                if self.files_staged:
                    self.restore()
                # reset renaming needs double-restoring
                if self.files_staged:
                    self.restore()
                raise ValueError(e)

        # generate diff, and restore changes for dry-runs
        diff = self._diff_changes()
        if diff and dryrun:
            self.restore()

        return diff

    def _select_assets_from_directory(self, directory: Path,
                                      depth: Union[int, None]) -> list[Path]:
        """
        Select all assets from `directory` and return them as a list.

        TODO: Enable this with changing the Repo.assets and Repo._get_assets()
              etc. for other attributes. See also #259
        """
        assets = []

        for path in directory.iterdir():
            # ignore .anchor and others
            if self._is_protected_path(path):
                continue

            # add files
            if path.is_file():
                assets.append(path)

            # add files from a directory recursively until depth is 0
            elif path.is_dir():
                # if flag --depth is used, but the max depth is reached, it
                # should skip folders and just care about the files anymore
                if depth is not None and depth == 0:
                    continue
                # before max depth is reached, go down one level more
                elif depth is not None and depth > 0:
                    assets += self._select_assets_from_directory(path, depth - 1)
                # flag is not set, so use infinite depth
                elif not depth:
                    assets += self._select_assets_from_directory(path, depth)

        return assets

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
    def _read_asset(asset: Path) -> dict:
        """
        Read and return the contents of an asset as a dictionary.
        """
        yaml = YAML(typ='rt', pure=True)
        contents = dict()
        try:
            contents = yaml.load(asset)
        except scanner.ScannerError as e:
            print(e)
        if contents is None:
            return dict()

        return contents

    def _set_sanitize(self, paths: Iterable[Union[Path, str]],
                      depth: Union[int, None]) -> list[Path]:
        """
        Check and normalize a list of paths. Traverse directories and select all
        assets from `paths` and return them as a list of absolute Paths.
        """
        error_path_absent = []
        error_path_protected = []
        paths_to_set = []

        if depth and depth < 0:
            log.error(f"depth values must be positive, but is {depth}.")
            raise ValueError(f"depth values must be positive, but is {depth}.")

        for p in paths:
            full_path = Path(self.opdir, p).resolve()

            # paths must exist
            if not full_path.exists():
                error_path_absent.append(p)
                continue

            # protected paths
            if self._is_protected_path(full_path):
                error_path_protected.append(p)
                continue

            if full_path.is_dir():
                paths_to_set += self._select_assets_from_directory(full_path, depth)
            else:
                paths_to_set.append(full_path)

        if error_path_absent:
            log.error('The following paths do not exist:\n' +
                      self._n_join(error_path_absent) + '\n' +
                      'Nothing was deleted.')
            raise FileNotFoundError('The following paths do not exist:\n' +
                                    self._n_join(error_path_absent))

        if error_path_protected:
            log.error('The following paths are protected by onyo:\n' +
                      self._n_join(error_path_protected) + '\n' +
                      'No directories were created.')
            raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                         self._n_join(error_path_protected))

        if len(paths_to_set) == 0:
            log.error("No assets selected.")
            raise ValueError("No assets selected.")

        return paths_to_set

    def _update_names(self, assets: list[Path], name_values: dict) -> None:
        """
        Set the pseudo key fields of an assets name (rename an asset file) from
        values of a dictionary and test that the new name is valid and
        available.
        """
        new_assets = []

        # count and request the needed faux serial numbers
        faux_serial_list = []
        if 'serial' in name_values.keys() and name_values['serial'] == 'faux':
            faux_number = len(assets)
            if faux_number > 0:
                faux_serial_list = self.generate_faux_serials(num=faux_number)

        for asset in assets:
            # split old name into parts
            [serial, model, make, type] = [field[::-1] for field in re.findall(r'(.*)\.(.*)_(.*)_(.*)', asset.name[::-1])[0]]
            fields = name_values.keys()

            # update name fields and build new asset name
            if "serial" in fields:
                if name_values["serial"] == "faux":
                    serial = faux_serial_list.pop()
                else:
                    serial = name_values["serial"]
            if "model" in fields:
                model = name_values["model"]
            if "make" in fields:
                make = name_values["make"]
            if "type" in fields:
                type = name_values["type"]
            new_name = Path(asset.parent, f"{type}_{make}_{model}.{serial}")

            # Check validity of the new asset name
            if new_name == asset.name:
                log.error(f"New asset names must be different than old names: '{new_name}'")
                raise ValueError(f"New asset names must be different than old names: '{new_name}'")

            if not self.valid_name(new_name):
                log.error(f"New asset name is not valid: '{new_name}'")
                raise ValueError(f"New asset name is not valid: '{new_name}'")

            self.valid_asset_path_and_name_available(new_name, new_assets)
            new_assets.append(new_name)

            self._git(["mv", str(asset), str(new_name)])

    @staticmethod
    def _write_asset(asset: Path, contents: dict) -> None:
        """
        Write contents into an asset file.
        """
        if contents == {}:
            asset.open('w').write("")
        else:
            yaml = YAML(typ='rt')
            yaml.dump(contents, asset)

    #
    # RM
    #
    def rm(self, paths: Union[Iterable[Union[Path, str]], Path, str], dryrun: bool = False) -> list[str]:
        """
        Delete ``asset``\\(s) and ``directory``\\(s).
        """
        if not isinstance(paths, (list, set)):
            paths = [paths]

        paths_to_rm = self._rm_sanitize(paths)

        if dryrun:
            ret = self._git(['rm', '-r', '--dry-run'] + [str(x) for x in paths_to_rm])
        else:
            # rm and commit
            ret = self._git(['rm', '-r'] + [str(x) for x in paths_to_rm])

        # TODO: change this to info
        log.debug('The following will be deleted:\n' +
                  '\n'.join([str(x.relative_to(self.opdir)) for x in paths_to_rm]))

        # return a list of rm-ed assets
        # TODO: should this also list the dirs?
        # TODO: is this relative to opdir or root? (should be opdir)
        return [r for r in re.findall("rm '(.*)'", ret)]

    def _rm_sanitize(self, paths: Iterable[Union[Path, str]]) -> list[Path]:
        """
        Check and normalize a list of paths.

        Returns a list of absolute Paths.
        """
        error_path_absent = []
        error_path_protected = []
        paths_to_rm = []

        for p in paths:
            full_path = Path(self.opdir, p).resolve()

            # paths must exist
            if not full_path.exists():
                error_path_absent.append(p)
                continue

            # protected paths
            if self._is_protected_path(full_path):
                error_path_protected.append(p)
                continue

            paths_to_rm.append(full_path)

        if error_path_absent:
            log.error('The following paths do not exist:\n' +
                      self._n_join(error_path_absent) + '\n' +
                      'Nothing was deleted.')
            raise FileNotFoundError('The following paths do not exist:\n' +
                                    self._n_join(error_path_absent))

        if error_path_protected:
            log.error('The following paths are protected by onyo:\n' +
                      self._n_join(error_path_protected) + '\n' +
                      'No directories were created.')
            raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                         self._n_join(error_path_protected))

        return paths_to_rm

    #
    # UNSET
    #
    def unset(self, paths: Iterable[Union[Path, str]], keys: list[str],
              dryrun: bool, quiet: bool, depth: Union[int]) -> str:

        # set and unset should select assets exactly the same way
        assets_to_unset = self._set_sanitize(paths, depth)

        if any([key in ["type", "make", "model", "serial"] for key in keys]):
            log.error("Can't unset pseudo keys (name fields are required).")
            raise ValueError("Can't unset pseudo keys (name fields are required).")

        for asset in assets_to_unset:
            contents = self._read_asset(asset)

            for field in keys:
                try:
                    del contents[field]
                except KeyError:
                    if not quiet:
                        log.info(f"Field {field} does not exist in {asset}")

            self._write_asset(asset, contents)
            self.add(asset)

        # generate diff, and restore changes for dry-runs
        diff = self._diff_changes()
        if diff and dryrun:
            self.restore()

        return diff
