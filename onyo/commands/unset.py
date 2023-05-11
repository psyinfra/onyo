from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import Repo, OnyoInvalidRepoError
from onyo.commands.edit import request_user_response

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def sanitize_paths(repo: Repo, paths: list[str]) -> set[Path]:
    """
    Validate paths, returning an error if paths are invalid.
    """
    formatted_paths = {Path(p).resolve() for p in paths}
    nonexistent = {p for p in formatted_paths if not p.exists()}
    if nonexistent:
        print(
            ('The following paths do not exist:\n{0}\nNothing was '
             'unset.').format('\n'.join(map(str, nonexistent))),
            file=sys.stderr)
        sys.exit(1)

    protected = {p for p in formatted_paths if repo._is_protected_path(p)}
    if protected:
        print(
            ('The following paths are protected by onyo:\n{0}\nNothing was '
             'unset.').format('\n'.join(map(str, protected))),
            file=sys.stderr)
        sys.exit(1)

    return formatted_paths


def unset(args: argparse.Namespace) -> None:
    """
    Remove the ``value`` of ``key`` for matching assets.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    The ``type``, ``make``, ``model``, and ``serial`` pseudo-keys cannot be
    changed, to rename a file(s) use ``onyo set --rename``.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used. If Onyo is invoked from outside of the Onyo repository, the root of
    the repository is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """
    # check flags for conflicts
    if args.quiet and not args.yes:
        print('The --quiet flag requires --yes.', file=sys.stderr)
        sys.exit(1)

    repo = None
    try:
        repo = Repo(Path.cwd(), find_root=True)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    diff = ""
    paths = sanitize_paths(repo, args.path)
    try:
        diff = repo.unset(
            paths, args.keys, args.dry_run, args.quiet, args.depth)
    except ValueError:
        sys.exit(1)

    # display changes
    if not args.quiet and diff:
        print("The following assets will be changed:")
        print(diff)
    elif args.quiet:
        pass
    else:
        print("No assets containing the specified key(s) could be found. No assets updated.")
        sys.exit(0)

    # commit or discard changes
    staged = sorted(repo.files_staged)
    if staged:
        if args.yes or request_user_response("Update assets? (y/n) "):
            repo.commit(repo.generate_commit_message(message=args.message,
                                                     cmd="unset",
                                                     keys=args.keys))
        else:
            repo.restore()
            # when names were changed, the first restoring just brings
            # back the name, but leaves working-tree unclean
            if repo.files_staged:
                repo.restore()
            if not args.quiet:
                print("No assets updated.")
