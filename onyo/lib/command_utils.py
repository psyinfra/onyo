from __future__ import annotations

import logging
import re
import shutil
import sys
from typing import Generator

from .consts import UNSET_VALUE
from .onyo import OnyoRepo

log: logging.Logger = logging.getLogger('onyo.command_utils')


def sanitize_args_config(git_config_args: list[str]) -> list[str]:
    r"""
    Check the git config arguments against a list of conflicting options. If
    conflicts are present, the conflict list will be printed and will exit with
    error.

    Returns the unmodified  git config args on success.
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
    return git_config_args


def fill_unset(assets: Generator[dict, None, None] | filter,
               keys: list[str]) -> Generator[dict, None, None]:
    r"""Fill values for missing `keys` in `assets` with `UNSET_VALUE`.

    Helper for the onyo-get command.

    Parameters
    ----------
    assets
      Asset dictionaries to fill.
    keys
      Keys for which to set `UNSET_VALUE` if not present in an asset.
    """
    for asset in assets:
        yield {k: UNSET_VALUE for k in keys} | asset


def natural_sort(assets: list[dict],
                 keys: list[str] | None = None,
                 reverse: bool = False) -> list[dict]:
    r"""Sort an asset list by a given list of `keys`.

    Parameters
    ----------
    assets
      Assets to sort.
    keys
      Keys to sort `assets` by. Default: ['path'].
    reverse
      Whether to sort in reverse order.
    """
    keys = keys or ['path']

    def sort_order(x, k):
        return [int(s) if s.isdigit() else s.lower()
                for s in re.split('([0-9]+)', str(x[k]))]

    for key in reversed(keys):
        assets = sorted(
            assets,
            key=lambda x: sort_order(x, key),
            reverse=reverse)

    return assets


def get_history_cmd(interactive: bool, repo: OnyoRepo) -> str:
    r"""
    Get the command used to display history. The appropriate one is selected
    according to the interactive mode, and basic checks are performed for
    validity.

    Returns the command on success.
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
