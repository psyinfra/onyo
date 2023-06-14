from pathlib import Path
import subprocess
import logging
from onyo.lib.exceptions import OnyoInvalidRepoError
from typing import Union, Iterable, Optional

log: logging.Logger = logging.getLogger('onyo.git')


class GitRepo(object):

    def __init__(self,
                 path: Path,
                 find_root: bool = False) -> None:
        """
        Instantiates a `GitRepo` object with `path` as the root directory.

        If `find_root=True` searches the root of a worktree from `path`.
        """
        self.root = GitRepo.find_root(path) if find_root else path.resolve()

        self._files: Union[set[Path], None] = None

    @staticmethod
    def find_root(path: Path) -> Path:
        """Returns the git worktree root `path` belongs to"""
        root = None
        try:
            ret = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                 cwd=path, check=True,
                                 capture_output=True, text=True)
            root = Path(ret.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise OnyoInvalidRepoError(f"'{path}' is not a Git repository.")
        return root

    def _git(self, args: list[str], *, cwd: Optional[Path] = None, raise_error: bool = True) -> str:
        """
        """
        if cwd is None:
            cwd = self.root

        log.debug(f"Running 'git {args}'")
        ret = subprocess.run(["git"] + args,
                             cwd=cwd, check=raise_error,
                             capture_output=True, text=True)
        return ret.stdout

    @property
    def files(self) -> set[Path]:
        """
        A `set` containing the absolute `Paths` of all files of a repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `Repo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `Repo.clear_caches()`.
        """
        if not self._files:
            self._files = self._get_files()
        return self._files

    def clear_caches(self, files: bool = True) -> None:
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
        if files:
            self._files = None

    def restore_staged(self) -> None:
        """Restore all staged files with uncommitted changes in the repository.

        If nothing is staged, returns with no error.
        """
        staged = self.files_staged
        if not staged:
            return
        self._git(['restore', '--source=HEAD', '--staged', '--worktree'] +
                  [str(file) for file in staged])
        # `Repo.restore()` gets used by all most commands that might change the
        # repository to revert changes, especially when users answer "no" to
        # user dialogs. It might also be used by the API to reset the repository
        # variable after doing some manual changes on files (e.g. with
        # subprocess).
        self.clear_caches()

    def restore(self, paths: Union[list[Path], Path]) -> None:
        """Call git-restore on `paths`.
        """
        if not paths:
            log.debug("No paths passed to restore. Nothing to do.")
            return
        if not isinstance(paths, list):
            paths = [paths]
        self._git(['restore'] + [str(p) for p in paths])

    def _get_files(self) -> set[Path]:
        """
        Return a set of all absolute `Path`s to files in the repository
        (except under .git).
        """
        log.debug('Acquiring list of files')
        files = {self.root / x for x in self._git(['ls-files', '-z']).split('\0') if x}
        return files

    def _get_files_changed(self) -> set[Path]:
        """
        Return a set of all absolute `Path`s to unstaged changes in the
        repository.
        """
        log.debug('Acquiring list of changed files')
        changed = {self.root / x for x in self._git(['diff', '-z', '--name-only']).split('\0') if x}
        return changed

    def _get_files_staged(self) -> set[Path]:
        """
        Return a set of all absolute `Path`s to staged changes in the
        repository.
        """
        log.debug('Acquiring list of staged files')
        staged = {self.root / x for x in self._git(['diff', '--name-only', '-z', '--staged']).split('\0') if x}
        return staged

    def _get_files_untracked(self) -> set[Path]:
        """
        Return a set of all absolute `Path`s to untracked files in the
        repository.
        """
        log.debug('Acquiring list of untracked files')
        untracked = {self.root / x for x in self._git(['ls-files', '-z', '--others', '--exclude-standard']).split('\0') if x}
        return untracked

    @property
    def files_changed(self) -> set[Path]:
        """
        Returns a `set` containing the absolute `Path`s of all changed files
        (according to git) of a repository.
        """
        return self._get_files_changed()

    @property
    def files_staged(self) -> set[Path]:
        """
        Returns a `set` containing the absolute `Path`s of all staged files
        (according to git) of a repository.
        """
        return self._get_files_staged()

    @property
    def files_untracked(self) -> set[Path]:
        """
        Returns a `set` containing the absolute `Path`s of all untracked files
        (according to git) of a repository.
        """
        return self._get_files_untracked()

    def is_clean_worktree(self) -> bool:
        """
        Check if the working tree for git is clean. Returns True or False.
        """

        changed = {str(x) for x in self.files_changed}
        staged = {str(x) for x in self.files_staged}
        untracked = {str(x) for x in self.files_untracked}

        if changed or staged or untracked:
            log.error('The working tree is not clean.')
            if changed:
                log.error('Changes not staged for commit:\n{}'.format(
                    '\n'.join(map(str, changed))))
            if staged:
                log.error('Changes to be committed:\n{}'.format(
                    '\n'.join(map(str, staged))))
            if untracked:
                log.error('Untracked files:\n{}'.format(
                    '\n'.join(map(str, untracked))))
            log.error(
                'Please commit all changes or add untracked files to '
                '.gitignore')
            return False
        return True

    def maybe_init(self, target_dir: Path) -> None:
        # Note: Why? git-init would do that
        # create target if it doesn't already exist
        target_dir.mkdir(exist_ok=True)

        # git init (if needed)
        if Path(target_dir, '.git').exists():
            log.info(f"'{target_dir}' is already a git repository.")
        else:
            ret = self._git(['init'], cwd=target_dir)
            # Note: What is it about capturing output everywhere only to spit it out again?
            log.info(ret.strip())
        self.root = target_dir

    def stage_and_commit(self, paths: Union[Iterable[Path], Path], message: str) -> None:
        if isinstance(paths, Path):
            paths = [paths]
        self._git(['add'] + [str(p) for p in paths])
        self._git(['commit', '-m', message])

    @staticmethod
    def is_git_path(path: Path) -> bool:
        # .git/*, .gitignore, .gitattributes, .gitmodules, etc.
        return '.git' in path.parts or path.name.startswith('.git')

    def add(self, targets: Union[Iterable[Path], Path, str]) -> None:
        """
        Perform ``git add`` to stage files.

        Paths are relative to ``repo.root``.
        """
        if isinstance(targets, (list, set)):
            tgts = [str(x) for x in targets]
        else:
            tgts = [str(targets)]

        for t in tgts:
            if not Path(self.root, t).exists():
                raise FileNotFoundError(f"'{t}' does not exist.")

        self._git(['add'] + tgts)
        # `Repo.add()` is used by most repo-changing commands, and it might be
        # used often by the API to change the repository, before manually
        # calling clear_cache() or after a file was changed with a subprocess
        # call. To always secure the integrity of the caches, we reset them all.
        self.clear_caches()

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

    def get_config(self, name: str) -> Union[str, None]:
        """
        Get the value for a configuration option specified by `name`.

        git-config is checked following its order of precedence (worktree,
        local, global, system). If the config name is not found, .onyo/config is
        checked.

        Returns a string with the config value on success. None otherwise.
        """
        # TODO: Move onyo-config code to OnyoRepo

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
        except KeyError as e:
            raise ValueError("Invalid config location requested. Valid options are: {}"
                             "".format(', '.join(location_options.keys()))) from e

        # git-config (with its full stack of locations to check)
        self._git(['config'] + location_arg + [name, value]).strip()
        log.debug(f"'config for '{location}' set '{name}': '{value}'")

        return True

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

    def mv(self,
           source: Union[Path, Iterable[Path]],
           destination: Path,
           dryrun: bool = False) -> str:
        """Call git-mv on paths provided by `source` and `destination`.

        Returns
        -------
        list of tuple of Path
          each tuple represents a move from a source file to a destination file
        """
        if isinstance(source, Path):
            source = [source]

        mv_cmd = ['mv']
        if dryrun:
            mv_cmd.append('--dry-run')
        mv_cmd.extend([str(p) for p in source])
        mv_cmd.append(str(destination))
        return self._git(mv_cmd)

    def rm(self, paths: Union[list[Path], Path], force: bool = False, dryrun: bool = False) -> str:
        """Call git-rm on `paths`

        Returns
        -------
        str
          stdout of the git-rm subprocess
        """
        if not isinstance(paths, list):
            paths = [paths]
        rm_cmd = ["rm", "-r" + ('f' if force else '')]
        if dryrun:
            rm_cmd.append("--dry-run")
        rm_cmd.extend([str(p) for p in paths])
        return self._git(rm_cmd)
