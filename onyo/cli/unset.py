from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
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
            Keys to unset in assets. Multiple keys can be given
            (e.g. **key1 key2 key3**).
        """
    ),

    'asset': dict(
        args=('-a', '--asset'),
        required=True,
        metavar="ASSET",
        nargs='+',
        help="""
            Assets to unset **KEY**s in.
        """
    ),

    'message': shared_arg_message,
}


def unset(args: argparse.Namespace) -> None:
    """
    Remove **KEY**\s from assets.

    Keys that are used in asset names (see the ``onyo.assets.filename``
    configuration option) cannot be unset.

    The contents of all modified assets are checked for validity before
    committing. If problems are found, Onyo will error and leave the assets
    unmodified.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    assets = [Path(a).resolve() for a in args.asset]
    unset_cmd(inventory,
              keys=args.keys,
              assets=assets,
              message='\n\n'.join(m for m in args.message) if args.message else None)
