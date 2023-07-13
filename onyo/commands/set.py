from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, set_ as set_cmd
from onyo.shared_arguments import path

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')

arg_rename = dict(
    args=('-r', '--rename'),
    required=False,
    default=False,
    action='store_true',
    help=(
        'Permit assigning values to pseudo-keys that would result in the '
        'asset(s) being renamed.'))

arg_keys = dict(
    args=('-k', '--keys'),
    required=True,
    metavar="KEYS",
    nargs='+',
    help=(
        'Specify key-value pairs to set in asset(s). Multiple pairs can '
        'be specified (e.g. key=value key2=value2)'))

arg_path = dict(
    args=('-p', '--path'),
    metavar='PATH',
    nargs='*',
    type=path,
    help='Asset(s) and/or directorie(s) to set KEY=VALUE in')


def set(args: argparse.Namespace) -> None:
    """
    Set the ``value`` of ``key`` for matching assets. If a key does not exist,
    it is added and set appropriately.

    Key names can be any valid YAML key name.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    The ``type``, ``make``, ``model``, and ``serial`` pseudo-keys can be set
    when the `--rename` flag is used. It will result in the file(s) being
    renamed.

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
    paths = [Path(p).resolve() for p in args.path] if args.path else None
    set_cmd(repo,
            paths,
            args.keys,
            args.filter,
            args.dry_run,
            args.rename,
            args.depth,
            args.quiet,
            args.yes,
            args.message)
