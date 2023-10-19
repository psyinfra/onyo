from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, mv as mv_cmd
from onyo.argparse_helpers import path
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_mv = {
    'source': dict(
        metavar='SOURCE',
        nargs='+',
        type=path,
        help='Asset(s) and/or directory(s) to move into DEST'),

    'destination': dict(
        metavar='DEST',
        type=path,
        help='Destination to move SOURCE(s) into'),

    'message': shared_arg_message,
}


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

    mv_cmd(repo, sources, destination, args.message)
