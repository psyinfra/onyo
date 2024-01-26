from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.argparse_helpers import file
from onyo.lib.commands import onyo_cat
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_cat = {
    'asset': dict(
        metavar='ASSET',
        nargs='+',
        type=file,
        help='Paths of asset(s) to print'),
}


def cat(args: argparse.Namespace) -> None:
    """Print the contents of ``ASSET`` file(s) to the terminal.

    At least one valid asset path is required. Assets can be given multiple times.
    If any path specified is invalid, no contents are printed and an error is raised.
    """
    paths = [Path(p).resolve() for p in args.asset]

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_cat(inventory,
             paths)
