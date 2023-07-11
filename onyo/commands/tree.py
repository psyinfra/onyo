from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, tree as tree_cmd

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def tree(args: argparse.Namespace) -> None:
    """
    List the assets and directories in ``DIRECTORY`` in the ``tree`` format.
    """

    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo, ['asset-yaml'])
    paths = [Path(p).resolve() for p in args.directory]
    tree_cmd(repo, paths)
