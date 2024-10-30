from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.argparse_helpers import StoreSortOption
from onyo.lib.commands import onyo_get
from onyo.lib.exceptions import OnyoCLIExitCode
from onyo.lib.filters import Filter
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    import argparse

args_get = {
    'depth': dict(
        args=('-d', '--depth'),
        metavar='DEPTH',
        type=int,
        required=False,
        default=0,
        help=r"""
            Descend up to **DEPTH** levels into the directories specified. A
            depth of **0** descends recursively without limit.
        """
    ),

    'keys': dict(
        args=('-k', '--keys'),
        metavar='KEY',
        nargs='+',
        help=r"""
            **KEY**s to print the values of. Pseudo-keys (information not stored
            in the asset file) are also available for queries.
            Dictionary subkeys can be addressed using a period (e.g. ``model.name``,
            ``model.year``, etc.)
        """
    ),

    'machine_readable': dict(
        args=('-H', '--machine-readable'),
        action='store_true',
        help=r"""
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
        help=r"""
            Criteria to match assets in the form ``KEY=VALUE``, where **VALUE**
            is a python regular expression. Pseudo-keys such as ``path`` can
            also be used. Dictionary subkeys can be addressed using a period
            (e.g. ``model.name``, ``model.year``, etc.) One can match keys that
            are not in the output. Special values supported are:

              * ``<dict>``
              * ``<list>``
              * ``<unset>``
        """
    ),

    'include': dict(
        args=('-i', '--include'),
        metavar='INCLUDE',
        nargs='+',
        help=r"""
            Assets or directories to query.
        """
    ),

    'exclude': dict(
        args=('-x', '--exclude'),
        metavar='EXCLUDE',
        nargs='+',
        help=r"""
            Assets or directories to exclude from the query.
            Note, that **DEPTH** does not apply to excluded paths.
        """
    ),

    'sort_ascending': dict(
        args=('-s', '--sort-ascending'),
        metavar='SORT_KEY',
        action=StoreSortOption,
        nargs='+',
        help=r"""
            Sort matches by **SORT-KEY** in ascending order.
            Can be given multiple times. Sorting by multiple **SORT-KEY** will be done in order
            (earlier given keys take precedence over subsequent keys).
            This can be intermixed with ``-s/--sort-descending``.
            Note, that if a **SORT-KEY** appears multiple times, the latest appearance will
            overrule what was specified before.
            One can sort by keys that are not in the output.
        """
    ),

    'sort_descending': dict(
        args=('-S', '--sort-descending'),
        metavar='SORT_KEY',
        action=StoreSortOption,
        nargs='+',
        help=r"""
            Sort matches by **SORT-KEY** in descending order.
            Can be given multiple times. Sorting by multiple **SORT-KEY** will be done in order
            (earlier given keys take precedence over subsequent keys).
            This can be intermixed with ``-s/--sort-ascending``.
            Note, that if a **SORT-KEY** appears multiple times, the latest appearance will
            overrule what was specified before.
            One can sort by keys that are not in the output.
        """
    ),
}

epilog_get = r"""
.. rubric:: Exit Status

The exit status is ``0`` if at least one result is found, ``1`` if there are no
results, and ``2`` if an error occurred.

These exit values match those of ``grep``.

.. rubric:: Examples

List all assets belonging to a user:

.. code:: shell

    $ onyo get --include accounting/Bingo\ Bob

List all laptops in the warehouse:

.. code:: shell

    $ onyo get --match type=laptop --include warehouse/

Get the path of all laptops of a specific make and model, and print in machine
parsable format (suitable for piping):

.. code:: shell

    $ onyo get --match type=laptop make=apple model=macbookpro --keys path --machine-readable
"""


def get(args: argparse.Namespace) -> None:
    r"""
    Return values of the requested **KEY**\ s for matching assets.

    If no **KEY**\ s are given, the path and all keys in the asset name are
    printed (see ``onyo.assets.name-format``). If no **PATH**\ s are given, the
    current working directory is used.

    In addition to keys in asset contents, **PSEUDO-KEYS** can be queried and
    matched.

      * ``is_asset_directory``: is the asset an Asset Directory
      * ``directory``: parent directory of the asset relative to repo root
      * ``path``: path of the asset relative to repo root

    By default, the results are sorted by ``path``.
    """
    includes = [Path(p).resolve() for p in args.include] if args.include else [Path.cwd()]
    excludes = [Path(p).resolve() for p in args.exclude] if args.exclude else None

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))

    filters = [Filter(f).match for f in args.match] if args.match else None

    results = onyo_get(inventory=inventory,
                       sort=args.sort,
                       include=includes,
                       exclude=excludes,
                       depth=args.depth,
                       machine_readable=args.machine_readable,
                       # Type annotation for callables as filters, somehow
                       # doesn't work with the bound method `Filter.match`.
                       # Not clear, what's the problem.
                       match=filters,  # pyre-ignore[6]
                       keys=args.keys)

    if not results:
        raise OnyoCLIExitCode("'onyo get' exits 1 when no results are found.", 1)
