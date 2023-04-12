from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Set

from onyo import Repo, OnyoInvalidRepoError
from onyo.commands.edit import request_user_response

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log = logging.getLogger('onyo')


def _sanitize_paths(repo: Repo, paths: list[str]) -> Set[Path]:
    """Validate paths, returning an error if paths are invalid"""
    formatted_paths = {Path(p) for p in paths}
    nonexistent = {p for p in formatted_paths if not p.exists()}
    if nonexistent:
        print(
            ('The following paths do not exist:\n{0}\nNothing was '
             'set.').format('\n'.join(map(str, nonexistent))),
            file=sys.stderr)
        sys.exit(1)

    protected = {p for p in formatted_paths if repo._is_protected_path(p)}
    if protected:
        print(
            ('The following paths are protected by onyo:\n{0}\nNothing was '
             'set.').format('\n'.join(map(str, protected))),
            file=sys.stderr)
        sys.exit(1)

    return formatted_paths


def set(args: argparse.Namespace, opdir: str) -> None:
    """
    Set the ``value`` of ``key`` for matching assets. If the key does not exist,
    it is added and set appropriately.

    Key names can be any valid YAML key name.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    The ``type``, ``make``, ``model``, and ``serial`` pseudo-keys can be set
    when the `--rename` flag is used. It will result in the file(s) being
    renamed.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used. If Onyo is invoked from outside of the Onyo repository, the root of
    the repository is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """
    repo = None

    # check flags for conflicts
    if args.quiet and not args.yes:
        print('The --quiet flag requires --yes.', file=sys.stderr)
        sys.exit(1)

    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    diff = ""
    paths = _sanitize_paths(repo, args.path)
    try:
        diff = repo.set(
            paths, args.keys, args.dry_run, args.rename, args.depth)
    except ValueError:
        sys.exit(1)

    # display changes
    if not args.quiet and diff:
        print("The following assets will be changed:")
        print(diff)
    elif args.quiet:
        pass
    else:
        print("The values are already set. No assets updated.")
        sys.exit(0)

    # commit or discard changes
    staged = sorted(repo.files_staged)
    if staged:
        if args.yes or request_user_response("Update assets? (y/n) "):
            repo.commit(repo.generate_commit_message(message=args.message,
                                                     cmd="set", keys=args.keys))
        else:
            repo.restore()
            # when names were changed, the first restoring just brings
            # back the name, but leaves working-tree unclean
            if repo.files_staged:
                repo.restore()
            if not args.quiet:
                print("No assets updated.")
