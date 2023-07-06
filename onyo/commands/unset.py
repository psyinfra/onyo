from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, unset as unset_cmd

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def unset(args: argparse.Namespace) -> None:
    """
    Remove the ``value`` of ``key`` for matching assets.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    The ``type``, ``make``, ``model``, and ``serial`` pseudo-keys cannot be
    changed, to rename a file(s) use ``onyo set --rename``.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used. If Onyo is invoked from outside of the Onyo repository, the root of
    the repository is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """

    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)
    paths = [Path(p).resolve() for p in args.path]
    unset_cmd(repo,
              paths,
              args.keys,
              args.filter,
              args.dry_run,
              args.quiet,
              args.yes,
              args.depth,
              args.message)
