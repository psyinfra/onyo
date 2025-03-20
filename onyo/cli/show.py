from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_show
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_show = {
    'base': dict(
        args=('-b', '--base-path'),
        required=False,
        default=None,
        nargs='?',
        help=r"""
            Base path that pseudokey-paths are relative to. Default is the
            repository root.
        """
    ),
    'path': dict(
        metavar='PATH',
        nargs='+',
        help=r"""
            Paths to serialize.
        """
    ),
}

epilog_show = r"""
.. rubric:: Examples

Display the YAML record of an asset (file or directory):

.. code:: shell

    $ onyo show accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

Print the YAML records of the entire repository:

.. code:: shell

    $ onyo show .

Print the YAML record of a directory and all children, relative to the ``admin``
directory:

.. code:: shell

    $ onyo show admin/Karl\ Krebs/ --base-path admin/
"""


def show(args: argparse.Namespace) -> None:
    r"""
    Serialize assets and directories into a multidocument YAML stream.

    The filesystem hierarchy is encoded in pseudokeys (e.g. ``onyo.path.parent``).
    Directories are included in the stream as needed.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.path]
    base = Path(args.base).resolve() if args.base else inventory.root

    onyo_show(inventory,
              paths,
              base=base)
