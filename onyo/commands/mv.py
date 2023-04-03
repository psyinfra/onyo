from __future__ import annotations
import sys
from typing import TYPE_CHECKING

from onyo import Repo, OnyoInvalidRepoError, OnyoProtectedPathError
from onyo.commands.edit import request_user_response

if TYPE_CHECKING:
    import argparse


def mv(args: argparse.Namespace, opdir: str) -> None:
    """
    Move ``source``\\(s) (assets or directories) to the ``destination``
    directory, or rename a ``source`` directory to ``destination``.

    Files cannot be renamed using ``onyo mv``. To do so, use ``onyo set``.
    """
    repo = None

    # check flags
    if args.quiet and not args.yes:
        print('The --quiet flag requires --yes.', file=sys.stderr)
        sys.exit(1)

    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    if not args.quiet:
        dryrun_list = None
        try:
            dryrun_list = repo.mv(args.source, args.destination, dryrun=True)
        except (FileExistsError, FileNotFoundError, NotADirectoryError, OnyoProtectedPathError, ValueError):
            sys.exit(1)

        print('The following will be moved:\n' +
              '\n'.join(f"'{x[0]}' -> '{x[1]}'" for x in dryrun_list))

        if not args.yes and not request_user_response("Save changes? No discards all changes. (y/n) "):
            print('Nothing was moved.')
            sys.exit(0)

    try:
        repo.mv(args.source, args.destination)
        repo.commit(repo.generate_commit_message(message=args.message, cmd="mv",
                                                 destination=args.destination))
    except (FileExistsError, FileNotFoundError, OnyoProtectedPathError, ValueError):
        sys.exit(1)
