from __future__ import annotations
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import Repo

if TYPE_CHECKING:
    import argparse


def init(args: argparse.Namespace, opdir: str) -> None:
    """
    Initialize an Onyo repository. The directory will be initialized as a git
    repository (if it is not one already), the ``.onyo/`` directory created and
    populated with config files, templates, etc. Everything will be committed.

    The current working directory will be initialized if neither ``directory``
    nor the ``onyo -C <dir>`` option are specified.

    Running ``onyo init`` on an existing repository is safe. It will not
    overwrite anything; it will exit with an error.
    """
    target_dir = Path(opdir)
    if args.directory:
        if Path(args.directory).is_absolute():
            target_dir = Path(args.directory)
        else:
            target_dir = Path(opdir, args.directory)

    try:
        Repo(target_dir, init=True)
    except (FileExistsError, FileNotFoundError):
        sys.exit(1)
