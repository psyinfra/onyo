from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import path
from onyo.lib.commands import onyo_get
from onyo.lib.filters import Filter
from onyo.lib.inventory import Inventory

if TYPE_CHECKING:
    import argparse

args_get = {
    'depth': dict(
        args=('-d', '--depth'),
        metavar='DEPTH',
        type=int,
        required=False,
        default=0,
        help="""
            Descend up to **DEPTH** levels into the directories specified. A
            depth of **0** descends recursively without limit.
        """
    ),

    'keys': dict(
        args=('-k', '--keys'),
        metavar='KEY',
        nargs='+',
        help="""
            **KEY**s to print the values of. Pseudo-keys (information not stored
            in the asset file) are also available for queries.
        """
    ),

    'machine_readable': dict(
        args=('-H', '--machine-readable'),
        action='store_true',
        help="""
            Useful for scripting. Do not print headers and separate values with
            a single tab instead of variable white space.
        """
    ),

    'match': dict(
        args=('-M', '--match'),
        metavar='MATCH',
        nargs='+',
        type=str,
        default=None,
        help="""
            Criteria to match assets in the form ``KEY=VALUE``, where **VALUE**
            is a python regular expression. Pseudo-keys such as ``path`` can
            also be used. Special values supported are:

              * ``<dict>``
              * ``<list>``
              * ``<unset>``
        """
    ),

    'path': dict(
        args=('-p', '--path'),
        metavar='PATH',
        type=path,
        nargs='+',
        help="""
            Assets or directories to query.
        """
    ),

    'sort_ascending': dict(
        args=('-s', '--sort-ascending'),
        action='store_true',
        default=False,
        help="""
            Sort output in ascending order (excludes ``--sort-descending``).
        """
    ),

    'sort_descending': dict(
        args=('-S', '--sort-descending'),
        action='store_true',
        default=False,
        help="""
            Sort output in descending order (excludes ``--sort-ascending``).
        """
    ),
}


def get(args: argparse.Namespace) -> None:
    """
    Return values of the requested **KEY**\s for matching assets.

    If no **KEY**\s are given, all keys in the asset name are printed (see
    ``onyo.assets.filename``). If no **PATH**\s are given, the current working
    directory is used.

    In addition to keys in asset contents, **PSEUDO-KEYS** can be queried and
    matched.

      * ``is_asset_directory``: is the asset an Asset Directory
      * ``path``: path of the asset from repo root

    By default, the results are sorted by ``path``.
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
