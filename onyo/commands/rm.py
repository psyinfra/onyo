from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, rm as rm_cmd
from onyo.shared_arguments import path

if TYPE_CHECKING:
    import argparse

arg_path = dict(
    dest='path',
    metavar='PATH',
    nargs='+',
    type=path,
    help='Asset(s) and/or directory(s) to delete')


def rm(args: argparse.Namespace) -> None:
    """
    Delete ``ASSET``\\(s) and ``DIRECTORY``\\(s).

    A list of all files and directories to delete will be presented, and the
    user prompted for confirmation.
    """
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)
    paths = [Path(p).resolve() for p in args.path]
    rm_cmd(repo, paths, args.quiet, args.yes, args.message)
