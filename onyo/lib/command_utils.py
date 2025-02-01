from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from .consts import (
    SORT_DESCENDING,
)
from .inventory import (
    Inventory,
    InventoryOperation,
)
from .ui import ui

if TYPE_CHECKING:
    from collections import UserDict
    from .consts import sort_t
    from typing import (
        Sequence,
        Tuple,
    )

log: logging.Logger = logging.getLogger('onyo.command_utils')


def allowed_config_args(git_config_args: list[str]) -> bool:
    r"""Check a list of arguments for disallowed ``git config`` flags.

    ``git-config`` stores configuration information in a variety of locations.
    This makes sure that such location flags aren't in the list (and ``--help``).

    A helper for ``onyo_config()``.

    Parameters
    ----------
    git_config_args
        The list of arguments to pass to ``git config``.

    Raises
    ------
    ValueError
        If a disallowed flag is detected.
    """

    # git-config supports multiple layers of git configuration. Onyo uses
    # ``--file`` to write to .onyo/config. Other options are excluded.
    forbidden_flags = ['--system',
                       '--global',
                       '--local',
                       '--worktree',
                       '--file',
                       '--blob',
                       '--help',
                       '-h',
                       ]

    for a in git_config_args:
        if a in forbidden_flags:
            raise ValueError("The following options cannot be used with onyo config:\n%s\nExiting. Nothing was set." %
                             '\n'.join(forbidden_flags))
    return True


def inline_path_diff(source: str | Path,
                     destination: str| Path) -> str:
    """
    Generate an inline diff of two paths.

    Renaming (i.e. changing the last element) is its own action, and does not
    group with other changes. Moves group with adjacent changes when possible.
    (e.g. a/b/c/d/one -> a/b/two: "a/{b/c/d -> b}/{one -> two}")

    Parameters
    ----------
    source
        Path of source.
    destination
        Path of destination.
    """

    if Path(source).is_absolute() or Path(destination).is_absolute():
        raise ValueError("Paths must be relative.")

    result = []

    s_parts = Path(source).parts
    d_parts = Path(destination).parts

    # Special case
    # No grouping is possible if either are one element long.
    if len(s_parts) == 1 or len(d_parts) == 1:
        return f"{'/'.join(s_parts)} -> {'/'.join(d_parts)}"

    #
    # Rename
    #
    # build suffix
    if s_parts[-1] == d_parts[-1]:
        suffix = s_parts[-1]
    else:
        suffix = f"{{{s_parts[-1]} -> {d_parts[-1]}}}"
    s_parts = s_parts[:-1]
    d_parts = d_parts[:-1]

    #
    # Move
    #
    while s_parts or d_parts:
        if s_parts[0] == d_parts[0]:
            # Either (but not both) would empty themselves.
            # So group all that is left.
            if (len(s_parts) == 1) ^ (len(d_parts) == 1):
                result.append(f"{{{'/'.join(s_parts)} -> {'/'.join(d_parts)}}}")
                break
            else:
                result.append(s_parts[0])
                s_parts = s_parts[1:]
                d_parts = d_parts[1:]
        else:
            # get the indexes of the /next/ mutual value
            ns, ds = intersect_index(s_parts[1:], d_parts[1:])
            ns = ns if ns is None else ns + 1 # correct index
            ds = ds if ds is None else ds + 1 # correct index

            if ns is None:
                # No more overlap between the two lists.
                # So group all that is left.
                result.append(f"{{{'/'.join(s_parts)} -> {'/'.join(d_parts)}}}")
                break
            else:
                # There is a future overlap. So group up until it.
                result.append(f"{{{'/'.join(s_parts[:ns])} -> {'/'.join(d_parts[:ds])}}}")
                s_parts = s_parts[ns:]
                d_parts = d_parts[ds:]

    result.append(suffix)

    return '/'.join(result)


def intersect_index(seq1: Sequence,
                    seq2: Sequence) -> Tuple[int | None, int | None]:
    """
    Compare two sequences. If a match is found, return both indexes of the match.

    Returns ``None`` as the indexes if no match is found.

    Parameters
    ----------
    seq1
        First sequence.
    seq2
        Second sequence.
    """
    for index1, item in enumerate(seq1):
        try:
            index2 = seq2.index(item)
            return (index1, index2)
        except ValueError:
            pass

    return (None, None)


def natural_sort(assets: list[dict | UserDict],
                 keys: dict[str, sort_t]) -> list[dict | UserDict]:
    r"""Sort an asset list by a list of ``keys``.

    Parameters
    ----------
    assets
        Assets to sort.
    keys
        Keys to sort ``assets`` by.
    reverse
        Whether to sort in reverse order.
    """
    import locale
    import natsort
    from onyo.lib.items import resolve_alias
    # set the locale for all categories to the user’s default setting
    locale.setlocale(locale.LC_ALL, '')

    for key in reversed(keys.keys()):
        alg = natsort.ns.LOCALE | natsort.ns.INT
        if resolve_alias(key).startswith('onyo.path'):
            alg |= natsort.ns.PATH
        assets = sorted(assets,
                        key=natsort.natsort_keygen(key=lambda x: x.get(key), alg=alg),
                        reverse=keys[key] == SORT_DESCENDING)

    return assets


def print_diff(diffable: Inventory | InventoryOperation) -> None:
    # This isn't nice yet. We need to consolidate `UI` to deal with that.
    # However, that requires figuring how to deal with issues, when
    # capturing output in tests and rich not realizing that.
    for line in diffable.diff():
        match line[0] if line else '':
            case '+':
                style = "green"
            case '-':
                style = "red"
            case '@':
                style = "bold"
            case _:
                style = ""

        ui.rich_print(line, style=style)
