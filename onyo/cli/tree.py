from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_tree
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_tree = {
    'directory': dict(
        metavar='DIRECTORY',
        nargs='*',
        help=r"""
            Directories to list.
        """
    ),
    'dirs_only': dict(
        args=("-d", "--dirs-only"),
        action="store_true",
        help=r"""
            Print only directories.
        """
    ),
}

epilog_tree = r"""
.. rubric:: Examples

List all assets and directories in a directory:

.. code:: shell

    $ onyo tree shelf

List only the room structure of a building:

.. code:: shell

    $ onyo tree --dirs-only building_3/

"""


def tree(args: argparse.Namespace) -> None:
    r"""
    List the assets and directories of **DIRECTORY**\ s in a tree-like format.

    If no directory is provided, the tree for the current working directory is
    listed.

    **DIRECTORY**\ s are printed sequentially. If one does not exist, or is not
    an inventory directory, no further trees will be printed and an error is
    returned.
    """
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    dirs = [(d, Path(d).resolve()) for d in args.directory]
    # use CWD if no dirs
    dirs = dirs if dirs else [('.', Path.cwd())]

    for (desc, d) in dirs:
        onyo_tree(inventory,
                  path=d,
                  description=desc,
                  dirs_only=args.dirs_only)
