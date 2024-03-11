from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import path
from onyo.lib.commands import onyo_mv
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_mv = {
    'source': dict(
        metavar='SOURCE',
        nargs='+',
        type=path,
        help="""
            Assets and/or directories to move into DEST.
        """
    ),

    'destination': dict(
        metavar='DEST',
        type=path,
        help="""
            Destination to move SOURCEs into.
        """
    ),

    'message': shared_arg_message,
}


def mv(args: argparse.Namespace) -> None:
    """
    Move SOURCEs (assets or directories) into the DEST directory, or rename a
    SOURCE directory to DEST.

    If DEST is an asset file, it will be converted into an Asset Directory and
    then the SOURCEs will be moved into it.

    Assets cannot be renamed using ``onyo mv``. Their names are generated from
    keys in their contents. To rename a file, use ``onyo set`` or ``onyo edit``.
    """
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))

    sources = [Path(p).resolve() for p in args.source]
    destination = Path(args.destination).resolve()

    onyo_mv(inventory=inventory,
            source=sources,
            destination=destination,
            message='\n\n'.join(m for m in args.message) if args.message else None)
