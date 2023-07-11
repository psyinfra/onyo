from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import cat as cat_cmd, fsck

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def cat(args: argparse.Namespace) -> None:
    """
    Print the contents of ``ASSET``\\(s) to the terminal without parsing.
    """
    paths = [Path(p).resolve() for p in args.asset]

    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo, ['asset-yaml'])
    cat_cmd(repo, paths)
