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
            Number of levels to descend into the directories specified by
            ``include``. A depth of ``0`` descends recursively without limit.
            Default is ``0``.
        """
    ),

    'keys': dict(
        args=('-k', '--keys'),
        metavar='KEY',
        nargs='+',
        help=r"""
            **KEY**s to print the values of.
            Default is asset-name keys and ``path``.
        """
    ),

    'machine_readable': dict(
        args=('-H', '--machine-readable'),
        action='store_true',
        help=r"""
            Print results in a machine-friendly format (no headers; separate
            values with a single tab) rather than a human-friendly format
            (headers and padded whitespace to align columns).
        """
    ),

    'match': dict(
        args=('-M', '--match'),
        metavar='MATCH',
        nargs='+',
        type=str,
        default=None,
        help=r"""
            Criteria to match in the form ``KEY=VALUE`` — where **VALUE** is a
            literal string or a python regular expression. All keys can be
            matched, and are not limited to those specified by ``--keys``.
            Special values supported are:

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
            Paths under which to query. Default is inventory root.
        """
    ),

    'exclude': dict(
        args=('-x', '--exclude'),
        metavar='EXCLUDE',
        nargs='+',
        help=r"""
            Paths to exclude (i.e. results underneath will not be returned).
        """
    ),

    'sort_ascending': dict(
        args=('-s', '--sort-ascending'),
        metavar='SORT_KEY',
        action=StoreSortOption,
        nargs='+',
        help=r"""
            Sort matches by **SORT-KEY** in ascending order. Multiple **SORT-KEY**s
            will be sorted in the order given. This can be intermixed with
            ``-s/--sort-descending``. All keys can be sorted, and are not limited
            to those specified by ``--keys``.
        """
    ),

    'sort_descending': dict(
        args=('-S', '--sort-descending'),
        metavar='SORT_KEY',
        action=StoreSortOption,
        nargs='+',
        help=r"""
            Sort matches by **SORT-KEY** in descending order. Multiple **SORT-KEY**s
            will be sorted in the order given. This can be intermixed with
            ``-s/--sort-ascending``. All keys can be sorted, and are not limited
            to those specified by ``--keys``.
        """
    ),

    'types': dict(
        args=('-t', '--types'),
        metavar="TYPES",
        nargs='+',
        choices=('assets', 'directories', 'templates'),
        default=["assets"],
        help=r"""
            Item types to query. Equivalent to ``onyo.is.asset=True``,
            ``onyo.is.directory=True``, and ``onyo.is.template=True``.
            Default is ``assets``.
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

    All keys, both on-disk YAML and **PSEUDO-KEYS**, can be queried, matched, and
    sorted. Dictionary subkeys are addressed using a period (e.g. ``model.name``).

      * ``onyo.is.asset``: is an asset
      * ``onyo.is.directory``: is a directory
      * ``onyo.is.template``: is a template
      * ``onyo.path.absolute``: absolute path of the item
      * ``onyo.path.name``: name of the item
      * ``onyo.path.parent`` (default alias: ``directory``): parent directory of the item relative to repo root
      * ``onyo.path.relative`` (default alias: ``path``): path of the item relative to repo root

    By default, the results are sorted by ``onyo.path.relative``.
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
                       keys=args.keys,
                       types=args.types)

    if not results:
        raise OnyoCLIExitCode("'onyo get' exits 1 when no results are found.", 1)
