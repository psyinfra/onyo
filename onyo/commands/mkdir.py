from __future__ import annotations
import sys
from typing import TYPE_CHECKING

from onyo import Repo, OnyoInvalidRepoError, OnyoProtectedPathError
from onyo.commands.edit import request_user_response

if TYPE_CHECKING:
    import argparse


def mkdir(args: argparse.Namespace, opdir: str) -> None:
    """
    Create ``directory``\(s). Intermediate directories will be created as needed
    (i.e. parent and child directories can be created in one call).

    An empty ``.anchor`` file is added to each directory, to ensure that git
    tracks it even when empty.

    If the directory already exists, or the path is protected, Onyo will throw
    an error. All checks are performed before creating directories.
    """
    repo = None
    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    try:
        repo.mkdir(args.directory)
    except (FileExistsError, OnyoProtectedPathError):
        sys.exit(1)

    # commit changes
    staged = sorted(repo.files_staged)
    if not args.quiet:
        print("The following directories will be created:")
        print(repo._n_join(staged))
    if args.yes or request_user_response("Save changes? No discards all changes. (y/n) "):
        repo.commit(repo.generate_commit_message(message=args.message,
                                                 cmd="mkdir"))
    else:
        repo.restore()
        if not args.quiet:
            print('No assets updated.')
