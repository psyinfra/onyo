from __future__ import annotations

import logging
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Union, Generator, Iterable, Optional, Tuple

from rich.console import Console

from .ui import ui
from .onyo import OnyoRepo
from .exceptions import OnyoInvalidFilterError
from .filters import Filter, UNSET_VALUE


log: logging.Logger = logging.getLogger('onyo.command_utils')

# Note: Several functions only stage changes. Implies: This function somewhat
# assumes commit to be called later, which is out of its own control.
# May be better to only do the modification and have the caller take care of
# what to do with those modifications.
# Related: Staging probably not necessary. We can commit directly. Saves
# overhead for git-calls and would only have a different effect if changes were
# already staged before an onyo operation and are to be included in the commit.
# Which sounds like a bad idea, b/c of obfuscating history. So, probably:
# have functions to assemble paths/modifications and commit at once w/o staging
# anything in-between.


# Note: logging for user messaging rather than logging progress along internal
# call paths. DataLad does, too, and it's bad. Conflates debugging with "real"
# output.


def sanitize_args_config(git_config_args: list[str]) -> list[str]:
    """
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


def sanitize_keys(k: Optional[list[str]],
                  defaults: list) -> list[str]:
    """
    Remove duplicates from k while preserving key order and return default
    (pseudo) keys if k is empty
    """
    seen = set()
    return [x for x in k if not (x in seen or seen.add(x))] if k else defaults


def set_filters(
        filters: list[str], repo: OnyoRepo, rich: bool = False) -> list[Filter]:
    """Create filters and check if there are no duplicate filter keys"""
    # Note: This is part of the get command

    init_filters = []
    try:
        init_filters = [Filter(f) for f in filters]
    except OnyoInvalidFilterError as exc:
        if rich:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {exc}')
        else:
            ui.print(exc, file=sys.stderr)
        # TODO: This raise replaces a sys.exit; Ultimately error messages above should be integrated in exception and
        #       rendering/printing handled upstairs.
        raise

    # ensure there are no duplicate filter keys
    duplicates = [
        x for x, i in Counter([f.key for f in init_filters]).items() if i > 1]
    if duplicates:
        if rich:
            console = Console(stderr=True)
            console.print(
                f'[red]FAILED[/red] Duplicate filter keys: {duplicates}')
        else:
            ui.print(f'Duplicate filter keys: {duplicates}', file=sys.stderr)
        # TODO: This raise replaces a sys.exit; Ultimately error messages above should be integrated in exception and
        #       rendering/printing handled upstairs.
        raise ValueError
    return init_filters


def fill_unset(
        assets: Generator[tuple[Path, dict[str, str]], None, None],
        keys: list, unset: str = UNSET_VALUE) -> Generator:
    """
    If a key is not present for an asset, define it as `unset`.
    """
    unset_keys = {key: unset for key in keys}
    for asset, data in assets:
        yield asset, unset_keys | data


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


def get_history_cmd(interactive: bool, repo: OnyoRepo) -> str:
    """
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


def unset(repo: OnyoRepo,
          paths: Iterable[Path],
          keys: list[str],
          depth: Union[int, None]) -> list[Tuple[Path, Dict, Iterable]]:

    from .assets import get_asset_files_by_path, PSEUDO_KEYS, get_asset_content
    from .onyo import dict_to_yaml
    # set and unset should select assets exactly the same way
    assets_to_unset = get_asset_files_by_path(repo.asset_paths, paths, depth)

    if any([key in PSEUDO_KEYS for key in keys]):
        raise ValueError("Can't unset pseudo keys (name fields are required).")

    modifications = []
    for asset_path in assets_to_unset:
        contents = get_asset_content(asset_path)
        prev_content = contents.copy()

        for field in keys:
            try:
                del contents[field]
            except KeyError:
                ui.log(f"Field {field} does not exist in {asset_path}")

        if prev_content != contents:
            from difflib import unified_diff
            diff = unified_diff(dict_to_yaml(prev_content).splitlines(keepends=True),
                                dict_to_yaml(contents).splitlines(keepends=True),
                                fromfile=str(asset_path),
                                tofile="Update",
                                lineterm="")
        else:
            diff = []
        modifications.append((asset_path, contents, diff))

    return modifications
