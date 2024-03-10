from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import path
from onyo.lib.commands import onyo_rm
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_rm = {
    'path': dict(
        metavar='PATH',
        nargs='+',
        type=path,
        help="""
            Assets and/or directories to delete.
        """
    ),

    'assets': dict(
        args=('-a', '--asset'),
        required=False,
        default=False,
        action='store_true',
        help="""
            Operate only on assets. Asset Files are removed. Asset Directories
            are converted into normal directories.

            This cannot be used with the ``--dir`` flag.
        """
    ),

    'dirs': dict(
        args=('-d', '--dir'),
        required=False,
        default=False,
        action='store_true',
        help="""
            Operate only on directories. Directories are removed. Asset
            Directories are converted into Asset Files.

            This cannot be used with the ``--asset`` flag.
        """
    ),

    'message': shared_arg_message,
}


def rm(args: argparse.Namespace) -> None:
    """
    Delete ASSETs and/or DIRECTORYs.

    Directories and asset directories are deleted along with their contents.

    The ``--asset`` and ``--dir` flags can be used to constrain actions to
    either assets or directories (respectively).

    If any of the given paths are invalid, Onyo will error and delete none of
    them.
    """
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.path]
    if args.assets and args.dirs:
        raise ValueError("'--dir' and '--asset' are mutually exclusive.")
    mode = "all"
    if args.assets:
        mode = "asset"
    elif args.dirs:
        mode = "dir"

    onyo_rm(inventory,
            paths=paths,
            mode=mode,  # pyre-ignore[6]  check doesn't understand that this is in fact one of "all", "asset", "dir"
            message='\n\n'.join(m for m in args.message) if args.message else None)
