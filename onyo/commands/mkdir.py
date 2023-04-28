from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, mkdir as mkdir_cmd

if TYPE_CHECKING:
    import argparse


def mkdir(args: argparse.Namespace) -> None:
    """
    Create ``directory``\\(s). Intermediate directories will be created as
    needed (i.e. parent and child directories can be created in one call).

    An empty ``.anchor`` file is added to each directory, to ensure that git
    tracks it even when empty.

    If the directory already exists, or the path is protected, Onyo will throw
    an error. All checks are performed before creating directories.
    """
    dirs = [Path(d).resolve() for d in args.directory]
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)
    mkdir_cmd(repo, dirs, args.quiet, args.yes, args.message)
