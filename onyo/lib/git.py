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
        Literal,
    )

log: logging.Logger = logging.getLogger('onyo.git')


class GitRepo(object):
    r"""An object representing a Git repository.

    Uses :py:mod:`subprocess` to execute git commands on a repository.

    Bare repositories are not supported.

    Attributes
    ----------
    root
        The absolute Path of the root of the git repository.
    """

    def __init__(self,
                 path: Path,
                 find_root: bool = False) -> None:
        r"""Instantiate a ``GitRepo`` object with ``path`` as the root directory.

        Parameters
        ----------
        path
            The absolute Path of a git repository.
        find_root
            Replace ``path`` with the results of :py:func:`find_root`. Thus any
            directory of a git repository can be passed as ``path``, not just
            the repo root.
        """

        self.root = GitRepo.find_root(path) if find_root else path.resolve()
        self._files: list[Path] | None = None

    @staticmethod
    def find_root(path: Path) -> Path:
        r"""Return the absolute path of the git worktree root that ``path``
        belongs to.

        Checks ``path`` itself and each of its parents.

        Parameters
        ----------
        path
            The Path to find the git worktree root for.

        Raises
        ------
        OnyoInvalidRepoError
            Neither ``path`` nor its parents are a git repository.
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
        r"""Run git commands and return the output.

        Parameters
        ----------
        args
            Arguments to append to the ``git`` command.
            e.g. ``args=['add', <file>]`` results in the system call
            ``git add <file>``.
        cwd
            Path to run commands from. Default to ``self.root``.
        raise_error
            Raise :py:exc:`subprocess.CalledProcessError` if the command returns
            with a non-zero exit code.
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

        This property is cached, and is reset automatically by :py:func:`commit()`.
        """

        if not self._files:
            self._files = self.get_files()

        return self._files

    def clear_cache(self) -> None:
        r"""Clear the cache of this instance of GitRepo.

        When the repository is modified using only the public API functions, the
        cache is consistent. This method is only necessary if the repository is
        modified otherwise.
        """

        self._files = None

    def get_files(self,
                  paths: Iterable[Path] | None = None) -> list[Path]:
        r"""Get the absolute ``Path``\ s of all tracked files under ``paths``.

        Parameters
        ----------
        paths
            Paths to limit the scope of the search to. The entire repo by default.
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
        r"""Whether the git worktree is clean.
        """

        return not bool(self._git(['status', '--porcelain']))

    def maybe_init(self) -> None:
        r"""Initialize ``self.root`` as a git repo, but not if it's already one.
        """

        # make sure target dir exists
        self.root.mkdir(exist_ok=True)

        if (self.root / '.git').exists():
            log.info(f"'{self.root}' is already a git repository.")
        else:
            ret = self._git(['init'])
            ui.log_debug(ret.strip())

    def commit(self,
               paths: Iterable[Path] | Path,
               message: str) -> None:
        r"""Stage and commit changes in git.

        Parameters
        ----------
        paths
            Paths to commit.
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
        r"""Whether ``path`` is a git file or directory.

        A "git path" is a path that is used by git itself (tracked or not) and
        therefore not valid for use by Onyo.

        Any path underneath a directory called ``.git`` and any basename
        starting with ``.git`` is considered a git path. e.g. ``.git/*``,
        ``.gitignore``, ``gitattributes``, ``.gitmodules``, etc.

        Parameters
        ----------
        path
          The path to check.
        """

        return '.git' in path.parts or path.name.startswith('.git')

    def get_config(self,
                   key: str,
                   path: Path | None = None) -> str | None:
        r"""Get the value of a configuration key.

        If no ``path`` is given, the configuration key is acquired according to
        ``git-config``'s order of precedence (worktree, local, global, system).

        Parameters
        ----------
        key
            Name of the configuration key to query. Follows Git's convention
            of "SECTION.NAME.KEY" to address a key in a git config file::

              [SECTION "NAME"]
                  KEY = VALUE
        path
            Path of a config file, rather than Git's default locations.
        """

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
                   location: Literal['system', 'global', 'local', 'worktree'] | Path | None = None
                  ) -> None:
        r"""Set the value of a configuration key.

        Parameters
        ----------
        key
            The name of the configuration key to set.
        value
            The value to set the configuration key to.
        location
            The location to set the key/value in. Valid locations are standard
            git-config locations (``'system'``, ``'global'``, ``'local'``, and
            ``'worktree'``) or a Path of a file. ``None`` will use
            ``git-config``'s default location (``'local'``).

        Raises
        ------
        ValueError
            ``location`` is invalid.
        """

        location_options = {
            'system': ['--system'],
            'global': ['--global'],
            'local': ['--local'],
            'worktree': ['--worktree'],
            None: []  # use Git's default behavior
        }
        try:
            location_arg = ['--file', str(location)] if isinstance(location, Path) \
                else location_options[location]
        except KeyError as e:
            raise ValueError("Invalid config location requested. Valid options are: {}"
                             "".format(', '.join(str(location_options.keys())))) from e

        self._git(['config'] + location_arg + [key, value])
        ui.log_debug(f"'config for '{location}' set '{key}': '{value}'")

    def get_hexsha(self,
                   commitish: str | None = None,
                   short: bool = False) -> str | None:
        r"""Return the hexsha of a given commit-ish.

        Will return ``None`` if querying the mother of all commits (i.e. "HEAD"
        of an empty repository).

        Parameters
        ----------
        commitish
            Any identifier that refers to a commit (defaults to "HEAD").
        short
            Return the abbreviated form of the hexsha.

        Raises
        ------
        ValueError
            ``commitish`` is unknown.
        """

        # Use --quiet to suppress the 'Needed a single revision' error message
        # when running this on a repo with no commits.
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
        r"""Return the full commit message of a commit-ish.

        Parameters
        ----------
        commitish
            Any identifier that refers to a commit (defaults to "HEAD").
        """

        return self._git(['log', commitish or 'HEAD', '-n1', '--pretty=%B'])

    def check_ignore(self,
                     ignore: Path,
                     paths: list[Path]) -> list[Path]:
        r"""Get the subset of ``paths`` that are matched by patterns defined in
        the ``ignore`` file.

        Parameters
        ----------
        ignore
            Path to a file containing exclude patterns (in the style of ``.gitignore``).
        paths
            Paths to check
        """

        try:
            output = self._git(['-c', f'core.excludesFile={str(ignore)}', 'check-ignore', '--no-index', '--verbose'] +
                               [str(p) for p in paths])
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                # None of `paths` were ignored. That's ok.
                return []
            raise

        excluded = []
        for line in output.splitlines():
            parts = line.split('\t')
            src_file = Path(parts[0].split(':')[0])
            if src_file == ignore:
                excluded.append(Path(parts[1]))

        return excluded

    def _parse_log_output(self,
                          lines: list[str]) -> dict:
        """Produce a commit dict (of one commit) from the output of ``git log``.

        A helper for :py:func:`history`.

        Parameters
        ----------
        lines
            List of text lines from ``git log`` for a single commit.
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

    def history(self,
                path: Path | None = None,
                n: int | None = None) -> Generator[dict, None, None]:
        """Yield commit dicts representing the history of ``path``.

        The history is acquired via ``git log`` (``git log --follow`` if a
        ``path`` is given).

        Parameters
        ----------
        path
            The Path to get the history of. Defaults to the repo root.
        n
            Limit history to ``n`` commits. ``None`` for no limit (default).
        """

        # TODO: Formatting the output with `--pretty` may simplify handling
        #       multi-line strings in git-log's output (rather than splitting
        #       lines and iterating), parsing git's metadata and Onyo's
        #       operations record, and remove the leading spaces for the commit
        #       message.
        # --pretty='format:commit: %H%nAuthor: %an (%ae)%nCommitter: %cn (%ce)%nCommitDate: %cI%nMessage:%n%B'
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
