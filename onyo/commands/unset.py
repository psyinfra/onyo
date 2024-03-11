from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import path
from onyo.lib.commands import onyo_unset as unset_cmd
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_unset = {
    'keys': dict(
        args=('-k', '--keys'),
        required=True,
        metavar="KEY",
        nargs='+',
        type=str,
        help="""
            KEYs to unset in assets. Multiple keys can be given
            (e.g. key1 key2 key3).
        """
    ),

    'path': dict(
        args=('-p', '--path'),
        required=True,
        metavar="PATH",
        nargs='+',
        type=path,
        help="""
            Assets unset KEYs in.
        """
    ),

    'message': shared_arg_message,
}


def unset(args: argparse.Namespace) -> None:
    """
    Remove ``KEY``\s from assets.

    Keys that are used in asset names (see the ``onyo.assets.filename``
    configuration option) cannot be unset.

    The contents of all modified assets are checked for validity before
    committing. If problems are found, Onyo will error and leave the assets
    unmodified.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.path]
    unset_cmd(inventory,
              keys=args.keys,
              paths=paths,
              message='\n\n'.join(m for m in args.message) if args.message else None)
