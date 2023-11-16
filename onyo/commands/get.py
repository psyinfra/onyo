from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path

from onyo import OnyoRepo
from onyo.lib.inventory import Inventory
from onyo.lib.filters import Filter
from onyo.lib.commands import onyo_get
from onyo.argparse_helpers import path
from onyo.shared_arguments import shared_arg_depth, shared_arg_match

if TYPE_CHECKING:
    import argparse

args_get = {
    'machine_readable': dict(
        args=('-H', '--machine-readable'),
        action='store_true',
        help=(
            'Display asset(s) separated by new lines, and keys by tabs instead '
            'of printing a formatted table')),

    'keys': dict(
        args=('-k', '--keys'),
        metavar='KEYS',
        nargs='+',
        help=(
            'Key value(s) to return. Pseudo-keys (information not stored in '
            'the asset file) are also available for queries')),

    'path': dict(
        args=('-p', '--path'),
        metavar='PATH',
        type=path,
        nargs='+',
        help='Asset(s) or directory(s) to search through'),

    'sort_ascending': dict(
        args=('-s', '--sort-ascending'),
        action='store_true',
        default=False,
        help='Sort output in ascending order (excludes --sort-descending)'),

    'sort_descending': dict(
        args=('-S', '-sort-descending'),
        action='store_true',
        default=False,
        help='Sort output in descending order (excludes --sort-ascending)'),

    'depth': shared_arg_depth,
    'match': shared_arg_match
}


def get(args: argparse.Namespace) -> None:
    """
    Return matching ``ASSET``\(s) and values corresponding to the requested
    ``KEY``\(s).

    If no key(s) are given, the keys used in asset names are returned.
    If no ``asset`` or ``directory`` is specified, the current working
    directory is used.

    Filters can make use of pseudo-keys (i.e., properties of assets, that are
    provided by onyo rather than the asset file, like 'path'). Values of the
    dictionary or list type, as well as assets missing a value can be referenced
    as '<dict>', '<list>', or '<unset>' instead of their contents, respectively.
    If a requested key does not exist, its output is displayed as '<unset>'.

    The ``value`` of filters can be a string or a Python regular expression.

    By default, the returned assets are sorted by their paths.
    """
    if args.sort_ascending and args.sort_descending:
        raise ValueError('--sort-ascending (-s) and --sort-descending (-S) cannot be '
                         'used together')
    sort = 'descending' if args.sort_descending else 'ascending'
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))

    paths = [Path(p).resolve() for p in args.path] if args.path else [Path.cwd()]
    filters = [Filter(f).match for f in args.match] if args.match else None
    onyo_get(inventory=inventory,
             sort=sort,
             paths=paths,
             depth=args.depth,
             machine_readable=args.machine_readable,
             # Type annotation for callables as filters, somehow
             # doesn't work with the bound method `Filter.match`.
             # Not clear, what's the problem.
             match=filters,  # pyre-ignore[6]
             keys=args.keys)
