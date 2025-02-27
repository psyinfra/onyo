from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import onyo_rmdir
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import (
    shared_arg_message,
    shared_arg_no_auto_message,
)

if TYPE_CHECKING:
    import argparse

args_rmdir = {
    'directory': dict(
        metavar='PATH',
        nargs='+',
        help=r"""
            Directories to delete; or Asset Directories to convert into Asset Files.
        """
    ),
    'message': shared_arg_message,
    'no_auto_message': shared_arg_no_auto_message,
}

epilog_rmdir = r"""
.. rubric:: Examples

Remove a user from a group:

.. code:: shell

    $ onyo rmdir accounting/Bingo\ Bob/

Convert an empty Asset Directory into an Asset File:

.. code:: shell

    $ onyo rmdir accounting/Bingo\ Bob/laptop_apple_macbook.oiw629/

"""


def rmdir(args: argparse.Namespace) -> None:
    r"""
    Delete **DIRECTORY**\ s or convert Asset Directories into Asset Files.

    If the **DIRECTORY** is not empty, does not exist, the path is protected, or
    the asset is already an Asset File, then Onyo will error and leave
    everything unmodified.
    """

    dirs = [Path(d).resolve() for d in args.directory]
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_rmdir(inventory,
               dirs=dirs,
               message='\n\n'.join(m for m in args.message) if args.message else None,
               auto_message=False if args.no_auto_message else None)
