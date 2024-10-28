from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_history
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_history = {
    'interactive': dict(
        args=('-I', '--non-interactive'),
        required=False,
        default=None,  # auto-detect interactive TTY
        action='store_false',
        help=r"""
            Use the non-interactive tool to display history.
        """
    ),

    'path': dict(
        metavar='PATH',
        nargs='?',
        help=r"""
            Path to display the history of.
        """
    ),
}

epilog_history = r"""
.. rubric:: Examples

See the history of all assets of a user:

.. code:: shell

    $ onyo history accounting/Bingo\ Bob
"""


def history(args: argparse.Namespace) -> None:
    r"""
    Display the history of **PATH**.

    Onyo attempts to automatically detect whether the TTY is interactive and use
    the appropriate history tool. Use ``--non-interactive`` to override this.

    The commands to display history are configurable using ``onyo config``:

      * ``onyo.history.interactive``
      * ``onyo.history.non-interactive``
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    path = Path(args.path).resolve() if args.path else Path.cwd()

    onyo_history(inventory,
                 path,
                 interactive=args.interactive)
