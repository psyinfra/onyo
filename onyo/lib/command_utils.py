from __future__ import annotations

import logging
import shutil
import sys
from typing import TYPE_CHECKING

from .consts import (
    SORT_DESCENDING,
    UNSET_VALUE,
)
if TYPE_CHECKING:
    from typing import (
        Generator,
    )

    from .onyo import OnyoRepo
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


def fill_unset(assets: Generator[dict, None, None] | filter,
               keys: list[str]) -> Generator[dict, None, None]:
    r"""Fill values for missing ``keys`` in ``assets`` with ``UNSET_VALUE``.

    A helper for the ``onyo get`` command.

    See Also
    --------
    onyo.lib.consts.UNSET_VALUE

    Parameters
    ----------
    assets
        Asset dictionaries to fill.
    keys
        Keys to create if not present in an asset, and set with ``UNSET_VALUE``.
    """
    for asset in assets:
        yield {k: UNSET_VALUE for k in keys} | asset


def natural_sort(assets: list[dict],
                 keys: dict[str, sort_t]) -> list[dict]:
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
    import natsort

    for key in reversed(keys.keys()):
        alg = natsort.ns.IGNORECASE | natsort.ns.INT
        if key == 'path':
            alg |= natsort.ns.PATH
        assets = sorted(assets,
                        key=natsort.natsort_keygen(key=lambda x: x.get(key), alg=alg),
                        reverse=keys[key] == SORT_DESCENDING)

    return assets


def get_history_cmd(interactive: bool,
                    repo: OnyoRepo) -> str:
    r"""Get the command to display history.

    The command is selected according to the (non)interactive mode, and
    ``which`` verifies that it exists.

    A helper for the ``onyo history`` command.

    Parameters
    ----------
    interactive
        Whether the CLI mode is interactive or not.
    repo
        The OnyoRepo to search through for the configuration.

    Raises
    ------
    ValueError
        If the configuration key is either not set or the configured history
        program cannot be found by ``which``.
    """
    history_cmd = None
    config_name = 'onyo.history.interactive'

    if not interactive or not sys.stdout.isatty():
        config_name = 'onyo.history.non-interactive'

    history_cmd = repo.get_config(config_name)
    if not history_cmd:
        raise ValueError(f"'{config_name}' is unset and is required to display history.\n"
                         f"Please see 'onyo config --help' for information about how to set it.")

    history_program = history_cmd.split()[0]
    if not shutil.which(history_program):
        raise ValueError(f"'{history_cmd}' acquired from '{config_name}'. "
                         f"The program '{history_program}' was not found. Exiting.")

    return history_cmd
