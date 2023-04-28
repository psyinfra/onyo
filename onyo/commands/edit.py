from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import edit as edit_cmd
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def edit(args: argparse.Namespace) -> None:
    """
    Open the ``asset`` file(s) using the editor specified by "onyo.core.editor",
    the environment variable ``EDITOR``, or ``nano`` (as a final fallback).

    When multiple asset files are given, Onyo will open them in sequence.

    After editing an ``asset``, the contents will be checked for valid YAML and
    also against any matching rules in ``.onyo/validation/``. If problems are
    found, the choice will be offered to reopen the editor to fix them, or abort
    and return to the original state.
    """

    paths = [Path(p).resolve() for p in args.asset]
    repo = OnyoRepo(Path.cwd(), find_root=True)
    edit_cmd(repo, paths, args.message, args.quiet, args.yes)
