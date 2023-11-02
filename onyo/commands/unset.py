from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import unset as unset_cmd
from onyo.argparse_helpers import path
from onyo.shared_arguments import (
    shared_arg_depth,
    shared_arg_filter,
    shared_arg_message,
)

if TYPE_CHECKING:
    import argparse

args_unset = {
    'keys': dict(
        args=('-k', '--keys'),
        required=True,
        metavar="KEYS",
        nargs='+',
        type=str,
        help=(
            'Specify keys to unset in assets. Multiple keys can be given '
            '(e.g. key key2 key3)')),

    'path': dict(
        args=('-p', '--path'),
        metavar="PATH",
        nargs='*',
        type=path,
        help='Asset(s) and/or directory(s) for which to unset values in'),

    'depth': shared_arg_depth,
    'filter': shared_arg_filter,
    'message': shared_arg_message,
}


def unset(args: argparse.Namespace) -> None:
    """
    Remove the ``value`` of ``key`` for matching ``ASSET``\s.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    The ``type``, ``make``, ``model``, and ``serial`` pseudo-keys cannot be
    changed, to rename a file(s) use ``onyo set --rename``.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """

    repo = OnyoRepo(Path.cwd(), find_root=True)
    paths = [Path(p).resolve() for p in args.path] if args.path else None
    unset_cmd(repo,
              paths,
              args.keys,
              args.filter,
              args.depth,
              message='\n\n'.join(m for m in args.message) if args.message else None)
