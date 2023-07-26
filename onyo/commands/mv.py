from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, mv as mv_cmd
from onyo.shared_arguments import path

if TYPE_CHECKING:
    import argparse

arg_source = dict(
    dest='source',
    metavar='SOURCE',
    nargs='+',
    type=path,
    help='Asset(s) and/or directory(s) to move into DEST')

arg_destination = dict(
    dest='destination',
    metavar='DEST',
    type=path,
    help='Destination to move SOURCE(s) into')


def mv(args: argparse.Namespace) -> None:
    """
    Move ``SOURCE``\\(s) (assets or directories) to the ``DEST`` directory, or
    rename a ``SOURCE`` directory to ``DEST``.

    Files cannot be renamed using ``onyo mv``. To do so, use ``onyo set``.
    """
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)

    # TODO: Figure whether args.source is actually always a list
    sources = [Path(p).resolve() for p in args.source]
    destination = Path(args.destination).resolve()

    mv_cmd(repo, sources, destination, args.quiet, args.yes, args.message)
