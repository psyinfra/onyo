from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, mv as mv_cmd

if TYPE_CHECKING:
    import argparse


def mv(args: argparse.Namespace) -> None:
    """
    Move ``source``\\(s) (assets or directories) to the ``destination``
    directory, or rename a ``source`` directory to ``destination``.

    Files cannot be renamed using ``onyo mv``. To do so, use ``onyo set``.
    """
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)

    # TODO: Figure whether args.source is actually always a list
    sources = [Path(p).resolve() for p in args.source]
    destination = Path(args.destination).resolve()

    mv_cmd(repo, sources, destination, args.quiet, args.yes, args.message)
