from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.exceptions import OnyoInvalidRepoError
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Generator,
        Iterable,
    )

log: logging.Logger = logging.getLogger('onyo.git')


class GitRepo(object):
    r"""Representation of a git repository.

    This relies on subprocesses running on a git worktree.
    Does not currently support bare repositories.

    Attributes
    ----------
    root: Path
      The absolute path to the root of the git worktree.
    """

    def __init__(self,
                 path: Path,
                 find_root: bool = False) -> None:
        r"""Instantiates a `GitRepo` object with `path` as the root directory.

        Parameters
        ----------
        path
          An absolute path to the root of a git repository.
        find_root
          `find_root=True` allows to search the root of a git worktree from a
          subdirectory, beginning at `path`, instead of requiring the root.
        """
        self.root = GitRepo.find_root(path) if find_root else path.resolve()
        self._files: list[Path] | None = None

    @staticmethod
    def find_root(path: Path) -> Path:
        r"""Returns the git worktree root `path` belongs to.

        Parameters
        ----------
        path
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
             cwd: Path | None = None,
             raise_error: bool = True) -> str:
        r"""A wrapper function for git calls, returning the output of commands.

        Parameters
        ----------
        args
          Arguments to specify the git call to run, e.g. args=['add', <file>]
          leads to a system call `git add <file>`.
        cwd
          Run git commands from `cwd`. Default: `self.root`.
        raise_error
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
        r"""Get the absolute ``Path``\ s of all tracked files.

        This property is cached, and is reset automatically on `GitRepo.commit()`.

        If changes are made by different means, use `GitRepo.clear_cache()` to
        reset the cache.
        """
        if not self._files:
            self._files = self.get_subtrees()
        return self._files

    def clear_cache(self) -> None:
        r"""Clear cache of this instance of GitRepo.

        Caches cleared are:
        - `GitRepo.files`

        If the repository is exclusively modified via public API functions, the
        cache of the `GitRepo` object is consistent. If the repository is
        modified otherwise, use of this function may be necessary to ensure that
        the cache does not contain stale information.
        """
        self._files = None

    def get_subtrees(self,
                     paths: Iterable[Path] | None = None) -> list[Path]:
        r"""Get tracked files in the subtrees rooted at `paths`.

        Parameters
        ----------
        paths
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
        r"""Check whether the git worktree is clean.

        Returns
        -------
        bool
          True if the git worktree is clean, otherwise False.
        """
        return not bool(self._git(['status', '--porcelain']))

    def maybe_init(self) -> None:
        r"""Initialize `self.root` as a git repository
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
        r"""Stage and commit changes in git.

        Parameters
        ----------
        paths
          List of paths to commit.
        message
          The git commit message.
        """
        if isinstance(paths, Path):
            paths = [paths]
        pathspecs = [str(p) for p in paths]
        self._git(['add'] + pathspecs)
        self._git(['commit', '-m', message, '--'] + pathspecs)
        self.clear_cache()

    @staticmethod
    def is_git_path(path: Path) -> bool:
        r"""Whether `path` is a git file or directory.

        A 'git path' is considered a path that is used by git
        itself (tracked or not) and therefore not valid for use
        by onyo, e.g. `.git/*`, `.gitignore`, `gitattributes`,
        `.gitmodules`, etc.
        Any path underneath a directory called `.git` and any
        basename starting with `.git` returns False.

        Parameters
        ----------
        path
          The path to check.

        Returns
        -------
        bool
          True if path is a git file or directory, otherwise False.
        """
        return '.git' in path.parts or path.name.startswith('.git')

    def get_config(self,
                   key: str,
                   path: Path | None = None) -> str | None:
        r"""Get the value for a configuration option specified by ``key``.

        By default, git-config is read following its order of precedence (worktree,
        local, global, system). If a ``path`` is given, this is read instead.

        Parameters:
        -----------
        key
          Name of the config variable to query. Follows the Git convention of
          "SECTION.NAME.KEY" to address a key in a git config file::

            [SECTION "NAME"]
              KEY = VALUE

        path
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
        if path:
            try:
                value = self._git(['config', '--file', str(path), '--get', key]).strip()
                ui.log_debug(f"config '{key}' acquired from {path}: '{value}'")
            except subprocess.CalledProcessError:
                ui.log_debug(f"config '{key}' missing in {path}")
        else:
            # git-config (with its full stack of locations to check)
            try:
                value = self._git(['config', '--get', key]).strip()
                ui.log_debug(f"git config acquired '{key}': '{value}'")
            except subprocess.CalledProcessError:
                ui.log_debug(f"git config missed '{key}'")
        return value

    def set_config(self,
                   key: str,
                   value: str,
                   location: str | Path | None = None) -> None:
        r"""Set the configuration option ``name`` to ``value``.

        Parameters
        ----------
        key
          The name of the configuration option to set.
        value
          The value to set for the configuration option.
        location
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

        self._git(['config'] + location_arg + [key, value])
        ui.log_debug(f"'config for '{location}' set '{key}': '{value}'")

    # Credit: Datalad
    def get_hexsha(self,
                   commitish: str | None = None,
                   short: bool = False) -> str | None:
        r"""Return the hexsha of a given commit-ish.

        Parameters
        ----------
        commitish
          Any identifier that refers to a commit (defaults to "HEAD").
        short
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
            return self._git(cmd).strip()
        except subprocess.CalledProcessError:
            if commitish is None:
                return None
            raise ValueError("Unknown commit identifier: %s" % commitish)

    def get_commit_msg(self,
                       commitish: str | None = None) -> str:
        r"""Returns the full commit message of a commit-ish.

        Parameters
        ----------
        commitish
            Any identifier that refers to a commit (defaults to "HEAD").

        Returns
        -------
        str
            the commit message including the subject line.
        """
        return self._git(['log', commitish or 'HEAD', '-n1', '--pretty=%B'])

    def check_ignore(self, ignore: Path, paths: list[Path]) -> list[Path]:
        r"""Get the `paths` that are matched by patterns defined in `ignore`.

        This is utilizing ``git-check-ignore`` to evaluate `paths` against
        a file `ignore`, that defines exclude patterns the gitignore-way.

        Parameters
        ----------
        ignore
          Path to a file containing exclude patterns to evaluate.
        paths
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

    def _parse_log_output(self, lines: list[str]) -> dict:
        """Generate a dict from the output of ``git log`` for one commit.

        Internal helper that converts a list of git-log-output lines of
        a single commit to a dictionary.
        """
        import datetime
        import re
        regex_author = re.compile(r"Author:\s+(?P<name>\b.*\b)\s+<(?P<email>[^\s]+)>$")
        regex_committer = re.compile(r"Commit:\s+(?P<name>\b.*\b)\s+<(?P<email>[^\s]+)>$")
        commit = dict()
        for line in lines:
            if line.startswith('commit '):
                commit['hexsha'] = line.split()[1]
                continue
            elif line.startswith('Author:'):
                try:
                    commit['author'] = re.match(regex_author, line).groupdict()  # pyre-ignore [16] AttributeError is caught
                except AttributeError as e:
                    if str(e).endswith("'groupdict'"):
                        raise RuntimeError(f"Unable to parse author-line:\n{line}") from e
                    raise
                continue
            elif line.startswith('AuthorDate:'):
                continue
            elif line.startswith('Commit:'):
                try:
                    commit['committer'] = re.match(regex_committer, line).groupdict()
                except AttributeError as e:
                    if str(e).endswith("'groupdict'"):
                        raise RuntimeError(f"Unable to parse committer-line:\n{line}") from e
                    raise
                continue
            elif line.startswith('CommitDate:'):
                commit['time'] = datetime.datetime.fromisoformat(line.split(maxsplit=1)[1])
                continue
            else:
                # This line is part of the message.
                if 'message' not in commit:
                    commit['message'] = [line]
                else:
                    commit['message'].append(line)

        return commit

    def history(self, path: Path | None = None, n: int | None = None) -> Generator[dict, None, None]:
        """Yields commit dicts representing the history of ``path``.

        History according to git log (git log --follow if a path is given).

        Parameters
        ----------
        path:
          What file to follow. If `None`, get the history of HEAD instead.
        n:
          Limit history going back ``n`` commits.
          ``None`` for no limit (default).
        """
        # TODO: Something like this may allow us to efficiently deal with multiline strings in git-log's output,
        #       rather than splitting lines and iterating over them when assembling output that belongs to a single
        #       commit, parsing the git data and then the operations record (also removes leading spaces for the commit
        #       message):
        #       --pretty='format:commit: %H%nAuthor: %an (%ae)%nCommitter: %cn (%ce)%nCommitDate: %cI%nMessage:%n%B'
        limit = [f'-n{n}'] if n is not None else []
        pathspec = ['--follow', '--', str(path)] if path else []
        cmd = ['log', '--date=iso-strict', '--pretty=fuller'] + limit + pathspec
        output = self._git(cmd)

        # yield output on a per-commit-basis
        commit_output = []
        for line in output.splitlines():
            if line.startswith('commit '):
                # This is the first line of a new commit.
                # 1. store previous commit output
                if commit_output:
                    # we just finished the previous commit.
                    yield self._parse_log_output(commit_output)
                # 2. start new commit output
                commit_output = [line]
            else:
                # add to current commit output
                commit_output.append(line)
        if commit_output:
            yield self._parse_log_output(commit_output)
