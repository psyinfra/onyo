from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_cat
from onyo.lib.exceptions import (
    InvalidAssetError,
    OnyoCLIExitCode,
)
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_cat = {
    'asset': dict(
        metavar='ASSET',
        nargs='+',
        help=r"""
            Paths of assets to print.
        """
    ),
}

epilog_cat = r"""
.. rubric:: Exit Status

The exit status is ``0`` if the asset contents are valid, ``1`` if the
contents are invalid, and ``2`` if an error occurred.

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

    If any of the paths are not assets, no content is printed and an error is
    returned.

    Assets with invalid content are printed with an error message. See **Exit
    Status** for more information about return codes.
    """
    paths = [Path(p).resolve() for p in args.asset]

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    try:
        onyo_cat(inventory,
                 paths)
    except InvalidAssetError as e:
        raise OnyoCLIExitCode("'onyo cat' exits 1 when invalid asset content is found.", 1) from e
