from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_edit
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.shared_arguments import (
    shared_arg_message,
    shared_arg_no_auto_message,
)

if TYPE_CHECKING:
    import argparse

args_edit = {
    'asset': dict(
        metavar='ASSET',
        nargs='+',
        help=r"""
            Paths of assets to edit.
        """
    ),
    'message': shared_arg_message,
    'no_auto_message': shared_arg_no_auto_message,
}

epilog_edit = r"""
.. rubric:: Examples

Edit an asset:

.. code:: shell

    $ onyo edit accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123
    <spawns editor>

Use ``sed`` to rename the key 'ram' to 'RAM' in all assets:

.. code:: shell

    $ ONYO_CORE_EDITOR="sed -i 's/ram:/RAM:/g'"
    $ onyo get --machine-readable --keys onyo.path.relative | xargs -d "\n" onyo --yes edit
"""


def edit(args: argparse.Namespace) -> None:
    r"""
    Open **ASSET**\ s in an editor.

    When multiple **ASSET**\ s are given, they are opened sequentially.

    The editor is selected by (in order):

      * ``ONYO_CORE_EDITOR`` environment variable
      * ``onyo.core.editor`` configuration option
      * ``core.editor`` configuration option (git)
      * ``EDITOR`` environment variable
      * ``nano`` (as a final fallback)

    ``ONYO_CORE_EDITOR`` is especially useful to programmatically modify assets
    with a utility (e.g. ``sed`` or ``jq``) or a bespoke script.

    The contents of all edited **ASSET**\ s are checked for validity before
    committing. If problems are found, a prompt is offered to either reopen the
    editor or discard the changes.
    """

    paths = [Path(p).resolve() for p in args.asset]
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_edit(inventory=inventory,
              paths=paths,
              message='\n\n'.join(m for m in args.message) if args.message else None,
              auto_message=False if args.no_auto_message else None)
