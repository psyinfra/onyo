from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.argparse_helpers import directory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_init = {
    'directory': dict(
        metavar='DIR',
        nargs='?',
        type=directory,
        help="""
            Initialize DIR as an Onyo repository.
        """
    )
}


def init(args: argparse.Namespace) -> None:
    """
    Initialize an Onyo repository.

    The current working directory will be initialized if neither ``DIR`` nor the
    ``onyo -C DIR`` flag are specified. If the target directory does not exist,
    it will be created.

    Initialization steps are:

      * create the target directory (if it does not exist)
      * initialize as a git repository (if it is not one already)
      * create the ``.onyo/`` directory, populate its contents, and commit

    Running ``onyo init`` on non-empty directories and git repositories is
    allowed. Only the ``.onyo`` directory will be committed. All other contents
    will be left in their state.

    Running ``onyo init`` repeatedly on a repository will not alter the
    contents, and will exit with an error.
    """
    target_dir = Path(args.directory).resolve() if args.directory else Path.cwd()
    OnyoRepo(target_dir, init=True)
