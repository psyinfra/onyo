from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import fsck as fsck_cmd

if TYPE_CHECKING:
    import argparse

epilog_fsck = r"""
.. rubric:: Examples

Check the validity of an Onyo repository:

.. code:: shell

    $ onyo fsck
"""


def fsck(args: argparse.Namespace) -> None:
    r"""
    Run a suite of integrity checks on the Onyo repository and its contents.

    The following tests are performed:

      * ``anchors``: directories (outside of .onyo) have an .anchor file
      * ``asset-yaml``: asset YAML is valid
      * ``clean-tree``: git has no changed (staged or unstaged) or untracked files

    Like Git, Onyo ignores files specified in ``.gitignore``.
    """
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck_cmd(repo)
