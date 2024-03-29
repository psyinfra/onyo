from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.argparse_helpers import StoreSingleKeyValuePairs
from onyo.lib.commands import onyo_set
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.shared_arguments import (
    shared_arg_message,
)

if TYPE_CHECKING:
    import argparse

args_set = {
    'rename': dict(
        args=('-r', '--rename'),
        required=False,
        default=False,
        action='store_true',
        help=r"""
            Allow setting **KEY**\ s that are part of the asset name.
            (see the ``onyo.assets.filename`` configuration option)
        """
    ),

    'keys': dict(
        args=('-k', '--keys'),
        required=True,
        action=StoreSingleKeyValuePairs,
        metavar="KEY",
        nargs='+',
        help=r"""
            **KEY-VALUE** pairs to set in assets. Multiple pairs can be given
            (e.g. ``key1=value1 key2=value2 key3=value3``).

            Quotes are necessary when using spaces or shell command characters:
            ```
            $ onyo set --keys title='Bob Bozniffiq: Saint of the Awkward' --asset ...
            ```
        """
    ),

    'asset': dict(
        args=('-a', '--asset'),
        required=True,
        metavar='ASSET',
        nargs='+',
        help=r"""
            Assets to set **KEY-VALUE**\ s in.
        """
    ),

    'message': shared_arg_message,
}


def set(args: argparse.Namespace) -> None:
    r"""
    Set **KEY**\ s to **VALUE**\ s for assets.

    **KEY** names can be any valid YAML key-name. If a key is not present in an
    asset, it is added and set appropriately.

    Setting **KEY**\ s that are used in the asset name requires the ``--rename``
    flag.

    In addition to keys in asset contents, some PSEUDO-KEYS can be set:

      * ``is_asset_directory``: boolean to control whether the asset is an
        Asset Directory.

    The contents of all modified assets are checked for validity before
    committing. If problems are found, Onyo will error and leave the assets
    unmodified.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    assets = [Path(a).resolve() for a in args.asset]
    onyo_set(inventory=inventory,
             assets=assets,
             keys=args.keys,
             rename=args.rename,
             message='\n\n'.join(m for m in args.message) if args.message else None)
