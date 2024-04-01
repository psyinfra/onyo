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

**Display the contents of an asset file**

.. code:: shell

    onyo cat accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

    type: laptop
    make: lenovo
    model: T490s
    serial: abc123
    RAM: 16GB
    display_size: '14.6'
    touch: yes
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
