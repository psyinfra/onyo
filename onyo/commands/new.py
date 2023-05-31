from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, new as new_cmd

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def new(args: argparse.Namespace) -> None:
    """
    Create new ``<path>/asset``\\(s) and add contents with ``--template``,
    ``--keys`` and ``--edit``. If the directories do not exist, they will be
    created.

    After the contents are added, the new ``assets``\\(s) will be checked for
    the validity of its YAML syntax and based on the rules in
    ``.onyo/validation/``.
    """
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)
    path = [Path(p).resolve() for p in args.path] if args.path else None
    tsv = Path(args.tsv).resolve() if args.tsv else None
    new_cmd(repo, path, args.template, tsv, args.keys, args.edit, args.yes, args.message)
