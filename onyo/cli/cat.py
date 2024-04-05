from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_cat
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_cat = {
    'asset': dict(
        metavar='ASSET',
        nargs='+',
        help='Paths of assets to print'
    ),
}

epilog_cat = r"""
.. rubric:: Examples

Display the contents of an asset (file or directory):

.. code:: shell

    $ onyo cat accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

Display the contents of all assets in a directory:

.. code:: shell

    $ onyo cat admin/Karl\ Krebs/*

Display the contents of an Asset Directory and all assets in it:

.. code:: shell

    $ onyo cat admin/Karl\ Krebs/laptop_apple_macbookpro.9sdjwb/{,*}
"""


def cat(args: argparse.Namespace) -> None:
    r"""
    Print the contents of **ASSET**\ s to the terminal.

    If any of the paths are invalid, then no contents are printed and an error
    is returned.
    """
    paths = [Path(p).resolve() for p in args.asset]

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_cat(inventory,
             paths)
