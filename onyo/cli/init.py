from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_init = {
    'directory': dict(
        metavar='DIR',
        nargs='?',
        help=r"""
            Directory to initialize as an Onyo repository.
        """
    )
}

epilog_init = r"""
.. rubric:: Examples

Initialize the current working directory as an Onyo repository:

.. code:: shell

    $ onyo init

Create a new directory and initialize it as an Onyo repository:

.. code:: shell

    $ onyo init new_inventory_directory
"""


def init(args: argparse.Namespace) -> None:
    r"""
    Initialize an Onyo repository.

    The current working directory is initialized if neither **DIR** nor the
    ``onyo -C DIR`` flag are specified. If the target directory does not exist,
    it is created.

    Initialization steps are:

      * create the target directory (if it does not exist)
      * initialize as a git repository (if it is not one already)
      * create the ``.onyo/`` directory, populate its contents, and commit

    Initializing non-empty directories and existing git repositories is allowed,
    and only the ``.onyo/`` directory and its contents are committed. All other
    contents are left in their state.

    Executing ``onyo init`` on an existing Onyo repository does not alter its
    contents, and exits with an error.
    """
    target_dir = Path(args.directory).resolve() if args.directory else Path.cwd()
    OnyoRepo(target_dir, init=True)
