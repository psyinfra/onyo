from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import directory
from onyo.lib.commands import onyo_tree
from onyo.lib.inventory import Inventory

if TYPE_CHECKING:
    import argparse

args_tree = {
    'directory': dict(
        metavar='DIR',
        nargs='*',
        type=directory,
        help='Directory(s) to print tree of')
}


def tree(args: argparse.Namespace) -> None:
    """List the assets and directories in ``DIRECTORY`` in the ``tree`` format.

    All given paths must be existing directories inside the onyo repository.
    They are tested for their validity in the beginning and only displayed if all paths are valid.

    If no path is specified, `onyo tree` prints the directory tree for CWD.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.directory]
    onyo_tree(inventory,
              paths)
