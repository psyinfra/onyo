import logging
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]
from onyo.utils import is_protected_path

logging.basicConfig()
log = logging.getLogger('onyo')


class OnyoInvalidRepoError(Exception):
    """Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    """Thrown if path is protected (.anchor, .git/, .onyo/)."""


class Repo:
    """
    """
    def __init__(self, path: Union[Path, str]) -> None:
        self._opdir = Path(path).resolve()
        self._root = self._get_root()
        # caches
        self._assets = None
        self._dirs = None
        self._files = None
        self._gitfiles = None

    @property
    def assets(self) -> set[Path]:
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

    def _get_assets(self) -> set[Path]:
        """
        Return a set of all assets in the repository.
        """
        assets = {x for x in self.files if not is_protected_path(x)}

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
        files = {Path(x) for x in self._git(['ls-files']).splitlines() if x}
        return files

    def _get_files_changed(self) -> set[Path]:
        """
        Return a set of all unstaged changes in the repository.
        """
        log.debug('Acquiring list of changed files')
        changed = {Path(x) for x in self._git(['diff', '--name-only']).splitlines() if x}
        return changed

    def _get_files_staged(self) -> set[Path]:
        """
        Return a set of all staged changes in the repository.
        """
        log.debug('Acquiring list of staged files')
        staged = {Path(x) for x in self._git(['diff', '--name-only', '--staged']).splitlines() if x}
        return staged

    def _get_files_untracked(self) -> set[Path]:
        """
        Return a set of all untracked files in the repository.
        """
        log.debug('Acquiring list of untracked files')
        untracked = {Path(x) for x in self._git(['ls-files', '--others', '--exclude-standard']).splitlines() if x}
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

    #
    # HELPERS
    #
    def _n_join(self, to_join: Iterable) -> str:
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
        """
        all_tests = {
            "clean-tree": self._fsck_clean_tree,
            "anchors": self._fsck_anchors,
            "asset-unique": self._fsck_unique_assets,
            "asset-yaml": self._fsck_yaml,
            "asset-validity": self._fsck_validation,
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
                            if not is_protected_path(x)}
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
    # MKDIR
    #
    def mkdir(self, directories: Union[Iterable[Union[Path, str]], Path, str]) -> None:
        """
        Create ``directory``\(s). Intermediate directories will be created as
        needed (i.e. parent and child directories can be created in one call).

        An empty ``.anchor`` file is added to each directory, to ensure that git
        tracks it even when empty.

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
        # paths should be relative to root in commit messages
        self.commit('mkdir: ' + ', '.join(["'{}'".format(x.relative_to(self.root)) for x in dirs]))

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
            if is_protected_path(full_dir):
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
        Move ``source``\(s) (assets or directories) to the ``destination``
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
            # mv and commit
            ret = self._git(['mv'] + [str(x) for x in src_paths] + [str(dest_path)])
            # TODO: should `mv` commit? (mkdir() does, add() doesn't)
            # TODO: can this commit message be made more helpful?
            # TODO: relative to self.root
            self.commit('moved asset(s)', src_paths)

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
        if is_protected_path(dest_path):
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
            if is_protected_path(full_path):
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
    # RM
    #
    def rm(self, paths: Union[Iterable[Union[Path, str]], Path, str], dryrun: bool = False) -> list[str]:
        """
        Delete ``asset``\(s) and ``directory``\(s).
        """
        if not isinstance(paths, (list, set)):
            paths = [paths]

        paths_to_rm = self._rm_sanitize(paths)

        if dryrun:
            ret = self._git(['rm', '-r', '--dry-run'] + [str(x) for x in paths_to_rm])
        else:
            # rm and commit
            ret = self._git(['rm', '-r'] + [str(x) for x in paths_to_rm])
            # TODO: should `rm` commit? (mkdir() does, add() doesn't)
            # TODO: can this commit message be made more helpful?
            # TODO: relative to self.root
            self.commit('deleted asset(s)', paths_to_rm)

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
            if is_protected_path(full_path):
                error_path_protected.append(p)
                continue

            paths_to_rm.append(full_path)

        if error_path_absent:
            log.error('The following paths do not exist:\n' +
                      '\n'.join(error_path_absent) + '\n' +
                      'Nothing was deleted.')
            raise FileNotFoundError('The following paths do not exist:\n' +
                                    '\n'.join(error_path_absent))

        if error_path_protected:
            log.error('The following paths are protected by onyo:\n' +
                      '\n'.join(error_path_protected) + '\n' +
                      'No directories were created.')
            raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                         '\n'.join(error_path_protected))

        return paths_to_rm
