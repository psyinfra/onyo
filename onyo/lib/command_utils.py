from __future__ import annotations

import logging
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

log: logging.Logger = logging.getLogger('onyo.command_utils')


def allowed_config_args(git_config_args: list[str]) -> bool:
    r"""Check a list of arguments for disallowed ``git config`` flags.

    ``git-config`` stores configuration information in a variety of locations.
    This makes sure that such location flags aren't in the list (and ``--help``).

    A helper for the ``onyo config`` command.

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

    # set the locale for all categories to the user’s default setting
    locale.setlocale(locale.LC_ALL, '')

    for key in reversed(keys.keys()):
        alg = natsort.ns.LOCALE | natsort.ns.INT
        if key == 'path':
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
        if line.startswith('+'):
            style = "green"
        elif line.startswith('-'):
            style = "red"
        elif line.startswith('@'):
            style = "bold"
        else:
            style = ""
        ui.rich_print(line, style=style)
