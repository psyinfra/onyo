from __future__ import annotations
import sys
from typing import TYPE_CHECKING

from onyo import Repo, OnyoInvalidRepoError, OnyoProtectedPathError
from onyo.commands.edit import request_user_response

if TYPE_CHECKING:
    import argparse


def rm(args: argparse.Namespace, opdir: str) -> None:
    """
    Delete ``asset``\(s) and ``directory``\(s).

    A list of all files and directories to delete will be presented, and the
    user prompted for confirmation.
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
            dryrun_list = repo.rm(args.path, dryrun=True)
        except (FileNotFoundError, OnyoProtectedPathError):
            sys.exit(1)

        print('The following will be deleted:\n' +
              '\n'.join(dryrun_list))

        if not args.yes and not request_user_response("Save changes? No discards all changes. (y/n) "):
            print('Nothing was deleted.')
            sys.exit(0)

    try:
        repo.rm(args.path)
        repo.commit(repo.generate_commit_message(message=args.message,
                                                 cmd="rm"))
    except (FileNotFoundError, OnyoProtectedPathError):
        sys.exit(1)
