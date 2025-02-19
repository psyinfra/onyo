from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.consts import (
    SORT_DESCENDING,
)
from onyo.lib.inventory import (
    Inventory,
    InventoryOperation,
)
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Sequence,
        Tuple,
    )
    from onyo.lib.consts import sort_t
    from onyo.lib.items import Item

log: logging.Logger = logging.getLogger('onyo.command_utils')


def allowed_config_args(git_config_args: list[str]) -> bool:
    r"""Check a list of arguments for disallowed ``git config`` flags.

    ``git-config`` stores configuration information in a variety of locations
    using location flags (e.g. ``--system``). Onyo uses ``--file`` to write to
    :py:data:`onyo.lib.consts.ONYO_CONFIG`.

    This function makes sure that such flags (and ``--help``) aren't in the
    list.

    A helper for py:func:`onyo.lib.commands.onyo_config`.

    Parameters
    ----------
    git_config_args
        List of arguments to pass to ``git config``.

    Raises
    ------
    ValueError
        A disallowed flag is detected.
    """

    forbidden_flags = ['--system', '--global', '--local', '--worktree',
                       '--file', '--blob',
                       '--help', '-h']
    if any([x in forbidden_flags for x in git_config_args]):
        raise ValueError("The following options cannot be used with onyo config:\n%s\nExiting. Nothing was set." %
                         '\n'.join(forbidden_flags))

    return True


def inline_path_diff(source: str | Path,
                     destination: str| Path) -> str:
    r"""Generate an inline diff of two paths.

    A **rename** (i.e. changing the last element) is its own action, and does
    not group with other changes. A **move** groups with adjacent changes when
    possible (e.g. a/b/c/d/one -> a/b/two: "a/{b/c/d -> b}/{one -> two}").

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
    # No grouping is possible if either is one element long.
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
    r"""Get the indexes of the first matching value of two sequences.

    Returns ``None`` as the indexes if no match is found.

    Parameters
    ----------
    seq1
        First sequence
    seq2
        Second sequence
    """

    for index1, item in enumerate(seq1):
        try:
            index2 = seq2.index(item)
            return (index1, index2)
        except ValueError:
            pass

    return (None, None)


def natural_sort(items: list[Item],
                 keys: dict[str, sort_t]) -> list[Item]:
    r"""Sort ``items`` according to a list of ``keys``.

    Parameters
    ----------
    items
        Items to sort.
    keys
        Keys to sort ``items`` by.
    reverse
        Sort in reverse order.
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
        items = sorted(items,
                       key=natsort.natsort_keygen(key=lambda x: x.get(key), alg=alg),
                       reverse=keys[key] == SORT_DESCENDING)

    return items


def print_diff(diffable: Inventory | InventoryOperation) -> None:
    r"""Print colorized diffs.

    The lines resulting from the object's ``diff()`` are colorized, with red or
    green corresponding to whether lines are removed or added.

    Parameters
    ----------
    diffable
        The object to print the diff of.
    """

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
