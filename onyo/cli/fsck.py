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

    By default, the following tests are performed:

      * ``clean-tree``: verify that git has no changed (staged or unstaged) or
        untracked files
      * ``anchors``: verify that all directories (outside of .onyo) have an
        .anchor file
      * ``asset-unique``: verify that all asset names are unique
      * ``asset-yaml``: verify that all asset contents are valid YAML
    """
    # TODO: Pass args and have a test; Actually - no args defined?
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck_cmd(repo)
