from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import onyo_unset as unset_cmd
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import (
    shared_arg_message,
    shared_arg_no_auto_message,
)

if TYPE_CHECKING:
    import argparse

args_unset = {
    'keys': dict(
        args=('-k', '--keys'),
        required=True,
        metavar="KEY",
        nargs='+',
        type=str,
        help=r"""
            Keys to unset in assets. Multiple keys can be given
            (e.g. **key1 key2 key3**). Dictionary subkeys can be addressed
            using a period (e.g. ``model.name``, ``model.year``, etc.).
            Note, that unsetting the last child of a dictionary does not
            remove the parent dictionary itself.
        """
    ),

    'asset': dict(
        args=('-a', '--asset'),
        required=True,
        metavar="ASSET",
        nargs='+',
        help=r"""
            Assets to unset **KEY**s in.
        """
    ),

    'message': shared_arg_message,
    'no_auto_message': shared_arg_no_auto_message,
}

epilog_unset = r"""
.. rubric:: Examples

Remove a key from an asset:

.. code:: shell

    $ onyo unset --keys USB_A --asset accounting/Bingo\ Bob/laptop_apple_macbook.oiw629

Remove a key from all laptops:

    $ onyo get --machine-readable --match type=laptop --keys path \
           | xargs -d "\n" onyo --yes unset --keys USB_A --asset
"""


def unset(args: argparse.Namespace) -> None:
    r"""
    Remove **KEY**\ s from assets.

    Keys that are used in asset names (see the ``onyo.assets.name-format``
    configuration option) cannot be unset.

    The contents of all modified assets are checked for validity before
    committing. If problems are found, Onyo errors and leaves the assets
    unmodified.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    assets = [Path(a).resolve() for a in args.asset]
    unset_cmd(inventory,
              keys=args.keys,
              assets=assets,
              message='\n\n'.join(m for m in args.message) if args.message else None,
              auto_message=False if args.no_auto_message else None)
