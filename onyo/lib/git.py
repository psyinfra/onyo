import logging
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from onyo.lib.exceptions import OnyoInvalidRepoError
from onyo.lib.ui import ui

log: logging.Logger = logging.getLogger('onyo.git')


class GitRepo(object):
    """
    An object to get and set git information, and to call git functions with.

    Attributes
    ----------
    root: Path
        The absolute path to the directory of the git worktree root.
    files: list of Path
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

        self._files: Optional[list[Path]] = None

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
    def files(self) -> list[Path]:
        """Get the absolute `Path`s of all tracked files.

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

    def get_subtrees(self,
                     paths: Optional[Iterable[Path]] = None) -> list[Path]:
        """"""
        # TODO: - We might want to consider untracked files as well. Would need `--others` in addition.
        #       - turn into issue
        ui.log_debug("Looking up tracked files%s",
                     f" underneath {', '.join([str(p) for p in paths])}" if paths else "")
        git_cmd = ['ls-files', '-z']
        if paths:
            git_cmd.extend([str(p) for p in paths])
        files = [self.root / x for x in self._git(git_cmd).split('\0') if x]
        return files

    def is_clean_worktree(self) -> bool:
        """Check whether the git worktree is clean.

        Returns
        -------
        bool
            True if the git worktree is clean, otherwise False.
        """
        return not bool(self._git(['status', '--porcelain']))

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
            ui.log_debug(ret.strip())
        self.root = target_dir

    def commit(self,
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
        self.clear_caches()

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
        file_: Path, optional
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
