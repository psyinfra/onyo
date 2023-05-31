from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse


def init(args: argparse.Namespace) -> None:
    """
    Initialize an Onyo repository. The directory will be initialized as a git
    repository (if it is not one already), the ``.onyo/`` directory created and
    populated with config files, templates, etc. Everything will be committed.

    The current working directory will be initialized if neither ``directory``
    nor the ``onyo -C <dir>`` option are specified.

    Running ``onyo init`` on an existing repository is safe. It will not
    overwrite anything; it will exit with an error.
    """
    target_dir = Path(args.directory).resolve() if args.directory else Path.cwd()
    OnyoRepo(target_dir, init=True)
