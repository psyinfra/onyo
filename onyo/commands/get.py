from __future__ import annotations
from collections import Counter
from typing import Generator, Union, TYPE_CHECKING
from pathlib import Path
import logging
import re
import sys

from rich import box
from rich.console import Console
from rich.table import Table

from onyo import Filter, Repo, OnyoInvalidRepoError, OnyoInvalidFilterError
from onyo.lib.filters import UNSET_VALUE

if TYPE_CHECKING:
    import argparse


logging.basicConfig()
log = logging.getLogger('onyo')


def natural_sort(
        assets: list[tuple[Path, dict[str, str]]],
        keys: Union[list, None] = None, reverse: bool = False) -> list:
    """
    Sort the output of `Repo.get()` by a given list of `keys` or by the path
    of the `assets` if no `keys` are provided.
    """
    if keys:
        for key in reversed(keys):
            assets = sorted(
                assets,
                key=lambda x: [
                    int(s) if s.isdigit() else s.lower() for s in
                    re.split('([0-9]+)', str(x[1][key]))],
                reverse=reverse)
    else:
        assets = sorted(
            assets,
            key=lambda x: [
                int(s) if s.isdigit() else s.lower()
                for s in re.split('([0-9]+)', str(x[0]))],
            reverse=reverse)

    return assets


def fill_unset(
        assets: Generator[tuple[Path, dict[str, str]], None, None],
        keys: list, unset: str = UNSET_VALUE) -> Generator:
    """
    If a key is not present for an asset, define it as `unset`.
    """
    unset_keys = {key: unset for key in keys}
    for asset, data in assets:
        yield asset, unset_keys | data


def set_filters(
        filters: list[str], repo: Repo, rich: bool = False) -> list[Filter]:
    """Create filters and check if there are no duplicate filter keys"""
    init_filters = []
    try:
        init_filters = [Filter(f, repo=repo) for f in filters]
    except OnyoInvalidFilterError as exc:
        if rich:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {exc}')
        else:
            print(exc, file=sys.stderr)
        sys.exit(1)

    # ensure there are no duplicate filter keys
    duplicates = [
        x for x, i in Counter([f.key for f in init_filters]).items() if i > 1]
    if duplicates:
        if rich:
            console = Console(stderr=True)
            console.print(
                f'[red]FAILED[/red] Duplicate filter keys: {duplicates}')
        else:
            print(f'Duplicate filter keys: {duplicates}', file=sys.stderr)
        sys.exit(1)
    return init_filters


def sanitize_keys(k: list[str], defaults: list) -> list[str]:
    """
    Remove duplicates from k while preserving key order and return default
    (pseudo) keys if k is empty
    """
    seen = set()
    k = [x for x in k if not (x in seen or seen.add(x))]
    return k if k else defaults


def get(args: argparse.Namespace, opdir: str) -> None:
    """
    Return matching asset(s) and values corresponding to the requested key(s).
    If no key(s) are given, the pseudo-keys are returned instead.

    Filters can make use of pseudo-keys (i.e., keys for which the values are
    only stored in the asset name). Values of the dictionary or list type, as
    well as assets missing a value can be referenced as '<dict>', '<list>',
    or '<unset>' instead of their contents, respectively. If a requested key
    does not exist, its output is displayed as '<unset>'.

    By default, the returned assets are sorted by their paths.
    """
    if args.sort_ascending and args.sort_descending:
        msg = (
            '--sort-ascending (-s) and --sort-descending (-S) cannot be used '
            'together')
        if args.machine_readable:
            print(msg, file=sys.stderr)
        else:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {msg}')
        sys.exit(1)

    repo = None
    try:
        repo = Repo(opdir)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    # validate arguments
    paths = set(Path(p) for p in args.path) or {Path('.')}
    invalid_paths = {p for p in paths if not p.exists()}
    paths -= invalid_paths
    if any(invalid_paths):
        for path in invalid_paths:
            print(
                f"cannot access '{path}': No such directory", file=sys.stderr)
        sys.exit(1)

    if args.depth < 0:
        print(
            f"-d, --depth must be 0 or larger, not '{args.depth}'",
            file=sys.stderr)
        sys.exit(1)

    keys = sanitize_keys(args.keys, defaults=repo.pseudo_keys)
    filters = set_filters(
        args.filter, repo=repo,
        rich=not args.machine_readable) if args.filter else None

    results = repo.get(
        keys=set(keys), paths=paths, depth=args.depth, filters=filters)
    results = fill_unset(results, keys, UNSET_VALUE)
    results = natural_sort(
        assets=list(results),
        keys=keys if args.sort_ascending or args.sort_descending else None,
        reverse=True if args.sort_descending else False)

    if args.machine_readable:
        sep = '\t'  # column separator
        for asset, data in results:
            values = sep.join([str(value) for value in data.values()])
            print(f'{values}{sep}{asset}')
    else:
        console = Console()
        table = Table(
            box=box.HORIZONTALS, title='', show_header=True,
            header_style='bold')

        for key in keys:
            table.add_column(key, no_wrap=True)

        table.add_column('path', no_wrap=True)

        if results:
            for asset, data in results:
                values = [str(value) for value in data.values()]
                table.add_row(*values, str(asset))

            console.print(table)
        else:
            console.print('No assets matching the filter(s) were found')
