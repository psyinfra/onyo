from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import onyo_mv
from onyo.lib.inventory import Inventory
from onyo.argparse_helpers import path
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_mv = {
    'source': dict(
        metavar='SOURCE',
        nargs='+',
        type=path,
        help='Asset(s) and/or directory(s) to move into DEST'),

    'destination': dict(
        metavar='DEST',
        type=path,
        help='Destination to move SOURCE(s) into'),

    'message': shared_arg_message,
}


def mv(args: argparse.Namespace) -> None:
    """
    Move ``SOURCE``\\(s) (assets or directories) to the ``DEST`` directory, or
    rename a ``SOURCE`` directory to ``DEST``.

    Files cannot be renamed using ``onyo mv``, since their names are generated from their contents.
    To rename a file, use ``onyo set``.
    """
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))

    sources = [Path(p).resolve() for p in args.source]
    destination = Path(args.destination).resolve()

    onyo_mv(inventory=inventory,
            source=sources,
            destination=destination,
            message='\n'.join(m for m in args.message) if args.message else None)
