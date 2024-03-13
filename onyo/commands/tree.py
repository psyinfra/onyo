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
        help='Directories to list'
    )
}


def tree(args: argparse.Namespace) -> None:
    """
    List the assets and directories of **DIRECTORY**\s in a tree-like format.

    If no directory is provided, the tree for the current working directory is
    listed.

    If any of the directories do not exist, then no tree is printed and an error
    is returned.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.directory]
    onyo_tree(inventory,
              paths)
