from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import onyo_mkdir
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import (
    shared_arg_message,
    shared_arg_no_auto_message,
)

if TYPE_CHECKING:
    import argparse

args_mkdir = {
    'directory': dict(
        metavar='DIR',
        nargs='+',
        help=r"""
            Directories to create; or assets to convert into an Asset Directory.
        """
    ),

    'message': shared_arg_message,
    'no_auto_message': shared_arg_no_auto_message,
}

epilog_mkdir = r"""
.. rubric:: Examples

Add a new user to a group:

.. code:: shell

    $ onyo mkdir accounting/Bingo\ Bob/

Convert an Asset File into an Asset Directory:

.. code:: shell

    $ onyo mkdir accounting/Bingo\ Bob/laptop_apple_macbook.oiw629

"""


def mkdir(args: argparse.Namespace) -> None:
    r"""
    Create **DIRECTORY**\ s or convert Asset Files into Asset Directories.

    Intermediate directories are created as needed (i.e. parent and child
    directories can be created in one call).

    If **DIRECTORY** is already a directory or a protected path, then Onyo
    errors and leaves everything unmodified.
    """
    dirs = [Path(d).resolve() for d in args.directory]
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_mkdir(inventory,
               dirs=dirs,
               message='\n\n'.join(m for m in args.message) if args.message else None,
               auto_message=False if args.no_auto_message else None)
