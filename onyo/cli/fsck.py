from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck as fsck_cmd

if TYPE_CHECKING:
    import argparse


def fsck(args: argparse.Namespace) -> None:
    """
    Run a suite of integrity checks on the Onyo repository and its contents.

    By default, the following tests are performed:

      * ``clean-tree``: verify that git has no changed (staged or unstaged) or
        untracked files
      * ``anchors``: verify that all directories (outside of .onyo) have an
        .anchor file
      * ``asset-unique``: verify that all asset names are unique
      * ``asset-yaml``: verify that all asset contents are valid YAML
      * ``asset-validity``: verify that all assets pass the validation rulesets
        defined in ``.onyo/validation/``
      * ``pseudo-keys``: verify that asset contents do not contain pseudo-key names
    """
    # TODO: Pass args and have a test; Actually - no args defined?
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck_cmd(repo)
