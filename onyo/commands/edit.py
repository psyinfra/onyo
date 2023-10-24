from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_edit
from onyo.lib.onyo import OnyoRepo
from onyo.lib.inventory import Inventory
from onyo.argparse_helpers import file
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_edit = {
    'asset': dict(
        metavar='ASSET',
        nargs='+',
        type=file,
        help='Paths of asset(s) to edit'),

    'message': shared_arg_message,
}


def edit(args: argparse.Namespace) -> None:
    """
    Open the ``ASSET``\(s) using the editor specified by "onyo.core.editor",
    the environment variable ``EDITOR``, or ``nano`` (as a final fallback).

    When multiple ``ASSET``\(s) are given, Onyo will open them in sequence.

    After editing an ``ASSET``, the contents will be checked for valid YAML.
    If problems are found, the choice will be offered to reopen the editor to
    fix them, or discard the invalid changes made.
    """

    paths = [Path(p).resolve() for p in args.asset]
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_edit(inventory=inventory,
              asset_paths=paths,
              message='\n\n'.join(m for m in args.message) if args.message else None)
