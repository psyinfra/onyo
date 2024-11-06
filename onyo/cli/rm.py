from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import onyo_rm
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import (
    shared_arg_message,
    shared_arg_no_auto_message,
)

if TYPE_CHECKING:
    import argparse

args_rm = {
    'path': dict(
        metavar='PATH',
        nargs='+',
        help=r"""
            Assets and/or directories to delete.
        """
    ),

    'recursive': dict(
        args=('-r', '--recursive'),
        required=False,
        default=False,
        action='store_true',
        help=r"""
            Remove directories recursively including their content.
        """
    ),

    'message': shared_arg_message,
    'no_auto_message': shared_arg_no_auto_message,
}

epilog_rm = r"""
.. rubric:: Examples

Delete an asset:

.. code:: shell

    $ onyo rm shelf/laptop_lenovo_T490s.abc123

Retire a user:

.. code:: shell

    $ onyo rm --message "Bob retired; he won at bingo" admin/Bingo\ Bob/
"""


def rm(args: argparse.Namespace) -> None:
    r"""
    Delete **ASSET**\ s and/or **DIRECTORY**\ s.

    Directories and asset directories are deleted along with their contents,
    if the ``--recursive`` flag is set. Otherwise, fails on non-empty directories.

    If any of the given paths are invalid, Onyo will error and delete none of
    them.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.path]

    onyo_rm(inventory,
            paths=paths,
            recursive=args.recursive,
            message='\n\n'.join(m for m in args.message) if args.message else None,
            auto_message=False if args.no_auto_message else None)
