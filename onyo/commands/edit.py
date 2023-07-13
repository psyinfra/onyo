from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import edit as edit_cmd
from onyo.lib.onyo import OnyoRepo
from onyo.shared_arguments import file

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')

arg_asset = dict(
    dest='asset',
    metavar='ASSET',
    nargs='+',
    type=file,
    help='Paths of asset(s) to edit')


def edit(args: argparse.Namespace) -> None:
    """
    Open the ``ASSET``\(s) using the editor specified by "onyo.core.editor",
    the environment variable ``EDITOR``, or ``nano`` (as a final fallback).

    When multiple ``ASSET``\(s) are given, Onyo will open them in sequence.

    After editing an ``ASSET``, the contents will be checked for valid YAML.
    If problems are found, the choice will be offered to reopen the editor to
    fix them, or discard the invalid changes made.
    """

    paths = [Path(p).resolve() for p in args.asset]
    repo = OnyoRepo(Path.cwd(), find_root=True)
    edit_cmd(repo, paths, args.message, args.quiet, args.yes)
