from pathlib import Path
import subprocess
import logging

from onyo.lib.ui import ui
from onyo.lib.exceptions import OnyoInvalidRepoError
from typing import Iterable, Optional

log: logging.Logger = logging.getLogger('onyo.git')


class GitRepo(object):
    """
    An object to get and set git information, and to call git functions with.

    Attributes
    ----------
    root: Path
        The absolute path to the directory of the git worktree root.

    files: set of Path
        A property containing the absolute Path to all files saved in git.
        This property is cached and consistent when only the public functions of
        GitRepo are called. Usage of private or external functions might
        require a manual reset of the cache with `GitRepo.clear_caches()`.
    """

    def __init__(self,
                 path: Path,
                 find_root: bool = False) -> None:
        """Instantiates a `GitRepo` object with `path` as the root directory.

        Parameters
        ----------
        path: Path
            An absolute path to the root of a git repository.

        find_root: bool
            `find_root=True` allows to search the root of a git worktree from a
            sub-directory, beginning at `path`, instead of requiring the root.
        """
        self.root = GitRepo.find_root(path) if find_root else path.resolve()

        self._files: Optional[set[Path]] = None

    @staticmethod
    def find_root(path: Path) -> Path:
        """Returns the git worktree root `path` belongs to.

        Parameters
        ----------
        path: Path
            The path to identify the git worktree root for. This can be any
            sub-directory of the repository, or the root directory itself.

        Returns
        -------
        Path
            An absolute path to the root of the git worktree where `.git/` is
            located.

        Raises
        ------
        OnyoInvalidRepoError
            If `path` is not inside a git repository at all.
        """
        root = None
        try:
            ret = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                 cwd=path, check=True,
                                 capture_output=True, text=True)
            root = Path(ret.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise OnyoInvalidRepoError(f"'{path}' is not a Git repository.")
        return root

    def _git(self,
             args: list[str], *,
             cwd: Optional[Path] = None,
             raise_error: bool = True) -> str:
        """A wrapper function for git calls that runs commands from the root
        directory and returns the output of commands.

        Parameters
        ----------
        args: list of str
            Arguments to specify the git call to run, e.g. args=['add', <file>]
            leads to a system call `git add <file>` from the root of git.

        cwd: Path, optional
            Run git commands from `cwd` instead of the root of the repository.

        raise_error: bool
            Specify if `subprocess.run()` is allowed to raise errors.

        Returns
        -------
        str
            Return the standard output from running the git command.
        """
        if cwd is None:
            cwd = self.root

        ui.log_debug(f"Running 'git {args}'")
        ret = subprocess.run(["git"] + args,
                             cwd=cwd, check=raise_error,
                             capture_output=True, text=True)
        return ret.stdout

    @property
    def files(self) -> set[Path]:
        """Get a `set` containing the absolute `Path`s of all files of a
        repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `Repo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `GitRepo.clear_caches()`.
        """
        if not self._files:
            self._files = self.get_subtrees()
        return self._files

    def clear_caches(self,
                     files: bool = True) -> None:
        """Clear caches of the instance of the GitRepo object.

        Paths to files in git are cached, and can become stale when the
        repository contents are modified. By default, this function clears the
        cache of all properties of the GitRepo.

        If the repository is exclusively modified via public API functions, the
        caches of the `GitRepo` object are consistent. If the repository is
        modified otherwise, this function clears the caches to ensure that the
        caches do not contain stale information.

        Parameters
        ----------
        files: bool
            Whether to reset the file cache.
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

    def restore(self,
                paths: list[Path] | Path) -> None:
        """Call git-restore on `paths`.

        Parameters
        ----------
        paths: list of Path
            The absolute Paths to the files or directories which are to be
            `git restore`d.
        """
        if not paths:
            ui.log_debug("No paths passed to restore. Nothing to do.")
            return
        if not isinstance(paths, list):
            paths = [paths]
        self._git(['restore'] + [str(p) for p in paths])

    def get_subtrees(self,
                     paths: Optional[Iterable[Path]] = None) -> set[Path]:
        """"""
        # TODO: - We might want to consider untracked files as well. Would need `--others` in addition.
        #       - turn into issue
        ui.log_debug("Looking up tracked files%s", f" underneath {', '.join([str(p) for p in paths])}" if paths else "")
        git_cmd = ['ls-files', '-z']
        if paths:
            git_cmd.extend([str(p) for p in paths])
        files = {self.root / x for x in self._git(git_cmd).split('\0') if x}
        return files

    def _get_files_changed(self) -> set[Path]:
        """Return a set of all absolute `Path`s to unstaged changes in the
        repository.
        """
        ui.log_debug('Acquiring list of changed files')
        changed = {self.root / x for x in self._git(['diff', '-z', '--name-only']).split('\0') if x}
        return changed

    def _get_files_staged(self) -> set[Path]:
        """Return a set of all absolute `Path`s to staged changes in the
        repository.
        """
        ui.log_debug('Acquiring list of staged files')
        staged = {self.root / x for x in self._git(['diff', '--name-only', '-z', '--staged']).split('\0') if x}
        return staged

    def _get_files_untracked(self) -> set[Path]:
        """Return a set of all absolute `Path`s to untracked files in the
        repository.
        """
        ui.log_debug('Acquiring list of untracked files')
        untracked = {self.root / x for x in self._git(['ls-files', '-z', '--others', '--exclude-standard']).split('\0') if x}
        return untracked

    @property
    def files_changed(self) -> set[Path]:
        """Get a `set` containing the absolute `Path`s of all changed files
        (according to git) of a repository.
        """
        return self._get_files_changed()

    @property
    def files_staged(self) -> set[Path]:
        """Get a `set` containing the absolute `Path`s of all staged files
        (according to git) of a repository.
        """
        return self._get_files_staged()

    @property
    def files_untracked(self) -> set[Path]:
        """Get a `set` containing the absolute `Path`s of all untracked files
        (according to git) of a repository.
        """
        return self._get_files_untracked()

    def is_clean_worktree(self) -> bool:
        """Check if the working tree for git is clean.

        Returns
        -------
        bool
            True if the git worktree is clean, otherwise False.
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

    def maybe_init(self,
                   target_dir: Path) -> None:
        """Initialize a directory as a git repository if it is not already one.

        Parameters
        ----------
        target_dir: Path
            A path to initialize as a git repository.
        """
        # Note: Why? git-init would do that
        # create target if it doesn't already exist
        target_dir.mkdir(exist_ok=True)

        # git init (if needed)
        if (target_dir / '.git').exists():
            log.info(f"'{target_dir}' is already a git repository.")
        else:
            ret = self._git(['init'], cwd=target_dir)
            # Note: What is it about capturing output everywhere only to spit it out again?
            ui.print(ret.strip())
        self.root = target_dir

    def stage_and_commit(self,
                         paths: Iterable[Path] | Path,
                         message: str) -> None:
        """Stage and commit changes in git.

        Parameters
        ----------
        paths: Path or Iterable of Path
            List of paths to files or directories for which to commit changes to
            git.

        message: str
            Specify the git commit message.
        """
        if isinstance(paths, Path):
            paths = [paths]
        self._git(['add'] + [str(p) for p in paths])
        self._git(['commit', '-m', message])

    @staticmethod
    def is_git_path(path: Path) -> bool:
        """Identifies if a path is a git file or directory, e.g.
        `.git/*`, `.gitignore`, `.gitattributes`, `.gitmodules`, etc.

        Parameters
        ----------
        path: Path
            The path to identify if it is a git file or directory, or if not.

        Returns
        -------
        bool
            True if path is a git file or directory, otherwise False.
        """
        return '.git' in path.parts or path.name.startswith('.git')

    def add(self,
            targets: Iterable[Path] | Path) -> None:
        """Perform ``git add`` to stage files.

        If called on files without changes, it does not raise an error.

        Parameters
        ----------
        targets: Path or Iterable of Path
            Paths are relative to ``repo.root``.

        Raises
        ------
        FileNotFoundError
            If a path in `targets` does not exist.
        """
        if isinstance(targets, (list, set)):
            tgts = [str(x) for x in targets]
        else:
            tgts = [str(targets)]

        for t in tgts:
            if not (self.root / t).exists():
                raise FileNotFoundError(f"'{t}' does not exist.")

        self._git(['add'] + tgts)
        # `Repo.add()` is used by most repo-changing commands, and it might be
        # used often by the API to change the repository, before manually
        # calling clear_cache() or after a file was changed with a subprocess
        # call. To always secure the integrity of the caches, we reset them all.
        self.clear_caches()

    def commit(self,
               *args) -> None:
        """Perform a ``git commit``.

        Parameters
        ----------
        args: tuple
            Components to compose the commit message from. At least one is
            required. The first argument is the title; each argument after it is
            a new paragraph. Lists and sets are printed one item per line.

        Raises
        ------
        ValueError
            If no commit message is provided.
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

    def get_config(self,
                   name: str,
                   file_: Optional[Path] = None) -> Optional[str]:
        """Get the value for a configuration option specified by `name`.

        By default, git-config is checked following its order of precedence (worktree,
        local, global, system). If a `file_` is given, this is checked instead.

        Parameters:
        -----------
        name: str
          Name of the config variable to query. Follows the Git convention of
          "SECTION.NAME.KEY" to address a key in a git config file:
            [SECTION "NAME"]
              KEY = VALUE
        file_: Path
          path to a config file to read instead of Git's default locations.

        Returns
        -------
        str or None
          the config value on success. None otherwise.
        """
        # TODO: lru_cache?
        # TODO: Not sure whether to stick with `file_` being alternative rather than fallback.
        #       Probably not, b/c then you can have onyo configs locally!
        #       However, this could be coming from OnyoRepo instead, since this is supposed to interface GIT.
        value = None
        if file_:
            try:
                value = self._git(['config', '--file', str(file_), '--get', name]).strip()
                ui.log_debug(f"config '{name}' acquired from {file_}: '{value}'")
            except subprocess.CalledProcessError:
                ui.log_debug(f"config '{name}' missing in {file_}")
        else:
            # git-config (with its full stack of locations to check)
            try:
                value = self._git(['config', '--get', name]).strip()
                ui.log_debug(f"git config acquired '{name}': '{value}'")
            except subprocess.CalledProcessError:
                ui.log_debug(f"git config missed '{name}'")
        return value

    def set_config(self,
                   name: str,
                   value: str,
                   location: str = 'onyo') -> bool:
        """Set the configuration option `name` to `value`.

        Parameters
        ----------
        name: str
            The name of the configuration option to set.

        value: str
            The value to set for the configuration option.

        location: str
            The location of the configuration for which the value should be set.
            Defaults to `onyo`. Other git config locations are: `system`,
            `global`, `local`, and `worktree`.

        Returns
        -------
        bool
            True on success, otherwise raises an exception.

        Raises
        ------
        ValueError
            If the config file was not found to set the value in.
        """
        location_options = {
            'onyo': ['--file', str(self.root / '.onyo/config')],
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
        ui.log_debug(f"'config for '{location}' set '{name}': '{value}'")

        return True

    def _diff_changes(self) -> str:
        """Query git for information about all uncommitted changes.

        Returns
        -------
        str
            A diff of all uncommitted changes. The format is a simplified
            version of `git diff`.
        """
        diff = self._git(['--no-pager', 'diff', 'HEAD']).splitlines()
        diff = [line.strip().replace("+++ b/", "\n").replace("+++ /dev/null", "\n")
                for line in diff if len(line) > 0 and line[0] in ['+', '-'] and not
                line[0:4] == '--- ' or "rename" in line]

        return "\n".join(diff).strip()

    def mv(self,
           source: Path | Iterable[Path],
           destination: Path) -> str:
        """Call git-mv on paths provided by `source` and `destination`.

        Parameters
        ----------
        source: list of Path
            Absolute paths of source files to move.

        destination: Path
            The absolute path of the destination to move `source` to.

        Returns
        -------
        str
            The standard output from running the `git mv` command subprocess.
        """
        if isinstance(source, Path):
            source = [source]

        mv_cmd = ['mv']
        mv_cmd.extend([str(p) for p in source])
        mv_cmd.append(str(destination))
        return self._git(mv_cmd)

    def rm(self,
           paths: list[Path] | Path,
           force: bool = False) -> str:
        """Call `git rm` on `paths`.

        Parameters
        ----------
        paths: Path or list of Path
            Absolute paths of files or directories to delete.

        force: bool
            Run `git rm` with option `--force`.

        Returns
        -------
        str
            The standard output from running the `git rm` command subprocess.
        """
        if not isinstance(paths, list):
            paths = [paths]
        rm_cmd = ["rm", "-r" + ('f' if force else '')]
        rm_cmd.extend([str(p) for p in paths])
        return self._git(rm_cmd)

    # Credit: Datalad
    def get_hexsha(self,
                   commitish: Optional[str] = None,
                   short: bool = False) -> Optional[str]:
        """Return a hexsha for a given commit-ish.

        Parameters
        ----------
        commitish: str, optional
            Any identifier that refers to a commit (defaults to "HEAD").
        short: bool
            Whether to return the abbreviated form of the hexsha.

        Returns
        -------
        str or None
            Returns string if no commitish was given and there are no commits yet, None.

        Raises
        ------
        ValueError
            If commit-ish is unknown.
        """
        # use --quiet because the 'Needed a single revision' error message
        # that is the result of running this in a repo with no commits
        # isn't useful to report
        cmd = ['rev-parse', '--quiet', '--verify',
               '{}^{{commit}}'.format(commitish if commitish else 'HEAD')]
        if short:
            cmd.append('--short')
        try:
            return self._git(cmd)
        except subprocess.CalledProcessError:
            if commitish is None:
                return None
            raise ValueError("Unknown commit identifier: %s" % commitish)

    def get_commit_msg(self,
                       commitish: Optional[str] = None) -> str:
        """Returns the full commit message of a commit-ish.

        Parameters
        ----------
        commitish: str, optional
            Any identifier that refers to a commit (defaults to "HEAD").

        Returns
        -------
        str
            the commit message including the subject line.
        """
        return self._git(['log', commitish or 'HEAD', '-n1', '--pretty=%B'])
