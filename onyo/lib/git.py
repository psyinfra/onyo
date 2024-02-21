import logging
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from onyo.lib.exceptions import OnyoInvalidRepoError
from onyo.lib.ui import ui

log: logging.Logger = logging.getLogger('onyo.git')


class GitRepo(object):
    """Representation of a git repository.

    This relies on subprocesses running on a git worktree.
    Does not currently support bare repositories.

    Attributes
    ----------
    root: Path
      The absolute path to the root of the git worktree.
    files: list of Path
      A property containing the absolute paths to all files tracked by git.
      This property is cached. Usage of private or external functions might
      require a manual reset via `GitRepo.get_subtree.cache_clear()`.
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
          subdirectory, beginning at `path`, instead of requiring the root.
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
          subdirectory of the repository, or the root directory itself.

        Returns
        -------
        Path
          An absolute path to the root of the git worktree.

        Raises
        ------
        OnyoInvalidRepoError
            If `path` is not inside a git repository at all.
        """
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
        """A wrapper function for git calls, returning the output of commands.

        Parameters
        ----------
        args: list of str
          Arguments to specify the git call to run, e.g. args=['add', <file>]
          leads to a system call `git add <file>`.
        cwd: Path, optional
          Run git commands from `cwd`. Default: `self.root`.
        raise_error: bool
          Whether to raise `subprocess.CalledProcessError` if the command
          returned with non-zero exitcode.

        Returns
        -------
        str
          Standard output of the git command.
        """
        cwd = cwd or self.root
        ui.log_debug(f"Running 'git {' '.join(args)}'")
        ret = subprocess.run(["git"] + args,
                             cwd=cwd, check=raise_error,
                             capture_output=True, text=True)
        return ret.stdout

    @property
    def files(self) -> list[Path]:
        """Get the absolute `Path`s of all tracked files.

        This property is cached. The cache is reset on `GitRepo.commit()`.
        If changes are made by different means, `GitRepo.clear_caches()`
        is available to reset the cache.
        """
        if not self._files:
            self._files = self.get_subtrees()
        return self._files

    def clear_cache(self) -> None:
        """Clear the `files` cache of this instance of GitRepo.

        Needed if changes to the repository are made by other means
        than `GitRepo.commit()`
        """
        self._files = None

    def get_subtrees(self,
                     paths: Optional[Iterable[Path]] = None) -> list[Path]:
        """Get tracked files in the subtrees rooted at `paths`.

        Parameters
        ----------
        paths: Iterable of Path
          Roots of subtrees to consider. The entire worktree by default.

        Returns
        -------
        list of Path
          Absolute paths to all tracked files within the given subtrees.
        """
        ui.log_debug("Looking up tracked files%s",
                     f" underneath {', '.join([str(p) for p in paths])}" if paths else "")
        git_cmd = ['ls-tree', '-r', '--full-tree', '--name-only', '-z', 'HEAD']
        if paths:
            git_cmd.extend([str(p) for p in paths])
        try:
            tree = self._git(git_cmd)
        except subprocess.CalledProcessError as e_ls_tree:
            try:
                self._git(['rev-parse', 'HEAD', '--'])
                raise e_ls_tree
            except subprocess.CalledProcessError:
                # no HEAD -> empty repository
                tree = ""
        files = [self.root / x for x in tree.split('\0') if x]
        return files

    def is_clean_worktree(self) -> bool:
        """Check whether the git worktree is clean.

        Returns
        -------
        bool
          True if the git worktree is clean, otherwise False.
        """
        return not bool(self._git(['status', '--porcelain']))

    def maybe_init(self) -> None:
        """Initialize `self.root` as a git repository
        if it is not already one.
        """
        # Note: Why? git-init would do that
        # create target if it doesn't already exist
        self.root.mkdir(exist_ok=True)

        # git init (if needed)
        if (self.root / '.git').exists():
            log.info(f"'{self.root}' is already a git repository.")
        else:
            ret = self._git(['init'])
            # Note: What is it about capturing output everywhere only to spit it out again?
            ui.log_debug(ret.strip())

    def commit(self,
               paths: Iterable[Path] | Path,
               message: str) -> None:
        """Stage and commit changes in git.

        Parameters
        ----------
        paths: Path or Iterable of Path
          List of paths to commit.
        message: str
          The git commit message.
        """
        if isinstance(paths, Path):
            paths = [paths]
        self._git(['add'] + [str(p) for p in paths])
        self._git(['commit', '-m', message])
        self.clear_cache()

    @staticmethod
    def is_git_path(path: Path) -> bool:
        """Whether `path` is a git file or directory.

        A 'git path' is considered a path that is used by git
        itself (tracked or not) and therefore not valid for use
        by onyo, e.g. `.git/*`, `.gitignore`, `gitattributes`,
        `.gitmodules`, etc.
        Any path underneath a directory called `.git` and any
        basename starting with `.git` returns False.

        Parameters
        ----------
        path: Path
          The path to check.

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

        By default, git-config is read following its order of precedence (worktree,
        local, global, system). If a `file_` is given, this is read instead.

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
          The config value if it exists. None otherwise.
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
                   location: Optional[str | Path] = None) -> None:
        """Set the configuration option `name` to `value`.

        Parameters
        ----------
        name: str
          The name of the configuration option to set.
        value: str
          The value to set for the configuration option.
        location: Path or str, optional
          The location of the configuration for which the value should
          be set. If a `Path`: config file to read, otherwise standard
          Git config locations: 'system', 'global', 'local',
          and 'worktree'. `None` means ``git-config``
          default behavior ('local'). Default: `None`.

        Raises
        ------
        ValueError
          If `location` is unknown.
        """
        location_options = {
            'system': ['--system'],
            'global': ['--global'],
            'local': ['--local'],
            'worktree': ['--worktree'],
            None: []  # Just go with Git's default behavior
        }
        try:
            location_arg = ['--file', str(location)] if isinstance(location, Path) \
                else location_options[location]
        except KeyError as e:
            raise ValueError("Invalid config location requested. Valid options are: {}"
                             "".format(', '.join(str(location_options.keys())))) from e

        self._git(['config'] + location_arg + [name, value])
        ui.log_debug(f"'config for '{location}' set '{name}': '{value}'")

    # Credit: Datalad
    def get_hexsha(self,
                   commitish: Optional[str] = None,
                   short: bool = False) -> Optional[str]:
        """Return the hexsha of a given commit-ish.

        Parameters
        ----------
        commitish: str, optional
          Any identifier that refers to a commit (defaults to "HEAD").
        short: bool
          Whether to return the abbreviated form of the hexsha.

        Returns
        -------
        str or None
          Hexsha of commitish. None, if querying the mother of all commits,
          i.e. 'HEAD' of an empty repository.

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

    def check_ignore(self, ignore: Path, paths: list[Path]) -> list[Path]:
        """Get the `paths` that are matched by patterns defined in `ignore`.

        This is utilizing ``git-check-ignore`` to evaluate `paths` against
        a file `ignore`, that defines exclude patterns the gitignore-way.

        Parameters
        ----------
        ignore: Path
          Path to a file containing exclude patterns to evaluate.
        paths: list of Path
          Paths to check against the patterns in `ignore`.

        Returns
        -------
        list of Path
          Paths in `paths` that are excluded by the patterns in `ignore`.
        """
        try:
            output = self._git(['-c', f'core.excludesFile={str(ignore)}', 'check-ignore', '--no-index', '--verbose'] +
                               [str(p) for p in paths])
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                # None of `paths` was ignored. That's fine.
                return []
            raise  # reraise on unexpected error
        excluded = []
        for line in output.splitlines():
            parts = line.split('\t')
            src_file = Path(parts[0].split(':')[0])
            if src_file == ignore:
                excluded.append(Path(parts[1]))
        return excluded

    # TODO: git check-ignore --no-index --stdin (or via command call)  ->  lazy, check GitRepo.files once. (Same invalidation)
    #       -> OnyoRepo would use it to maintain a ignore list from a (top-level .onyoignore)? .onyo/ignore ? Both?
