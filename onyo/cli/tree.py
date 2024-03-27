from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import onyo_tree
from onyo.lib.inventory import Inventory

if TYPE_CHECKING:
    import argparse

args_tree = {
    'directory': dict(
        metavar='DIR',
        nargs='*',
        help='Directories to list'
    )
}


def tree(args: argparse.Namespace) -> None:
    r"""
    List the assets and directories of **DIRECTORY**\ s in a tree-like format.

    If no directory is provided, the tree for the current working directory is
    listed.

    If any of the directories do not exist, then no tree is printed and an error
    is returned.
    """
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    dirs = [(d, Path(d).resolve()) for d in args.directory]
    # use CWD if no dirs
    dirs = dirs if dirs else [('.', Path.cwd())]

    onyo_tree(inventory,
              dirs)
