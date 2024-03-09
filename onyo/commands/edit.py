from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.argparse_helpers import file
from onyo.lib.commands import onyo_edit
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_edit = {
    'asset': dict(
        metavar='ASSET',
        nargs='+',
        type=file,
        help='Paths of ASSETs to edit.'
    ),

    'message': shared_arg_message,
}


def edit(args: argparse.Namespace) -> None:
    """
    Open ``ASSET``\s using an editor.

    When multiple ASSETs are given, they are opened sequentially.

    The editor is selected by (in order):

        * configuration option `onyo.core.editor`
        * ``EDITOR`` environment variable
        * ``nano`` (as a final fallback)

    The contents of all edited ASSETs are checked for validity before
    committing. If problems are found, a prompt is offered to either reopen the
    editor or discard the changes.
    """

    paths = [Path(p).resolve() for p in args.asset]
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_edit(inventory=inventory,
              paths=paths,
              message='\n\n'.join(m for m in args.message) if args.message else None)
