from __future__ import annotations

import copy
import logging
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Generator, Literal, ParamSpec, TypeVar
from functools import wraps

from rich import box
from rich.table import Table

from onyo.lib.command_utils import fill_unset, natural_sort
from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.exceptions import (
    OnyoRepoError,
    OnyoInvalidRepoError,
    PendingInventoryOperationError,
    NotADirError,
    NotAnAssetError,
    NoopError,
)
from onyo.lib.inventory import Inventory, OPERATIONS_MAPPING
from onyo.lib.onyo import OnyoRepo
from onyo.lib.ui import ui
from onyo.lib.utils import deduplicate, write_asset_file

log: logging.Logger = logging.getLogger('onyo.commands')

T = TypeVar('T')
P = ParamSpec('P')


def raise_on_inventory_state(func: Callable[P, T]) -> Callable[P, T]:
    r"""Raises if it's not OK to run an onyo command on `inventory`.

    Decorator for onyo commands. Expects an `Inventory` to be part of
    the arguments to the decorated function.

    Notes
    -----
    Currently simply assesses whether the worktree is clean and there
    are no pending operations in `inventory`.
    This may change to a more finegrained assessment of what kinds
    of commands can safely run on the current state of `inventory`.
    For example: `onyo_cat` could be allowed to run on a dirty worktree,
    or at least if there are no modifications to the asset file(s) it's
    supposed to print while not caring for modifications to other files.
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        inventory = None
        for o in list(args) + list(kwargs.values()):  # pyre-ignore[16]
            if isinstance(o, Inventory):
                inventory = o
                break
        if inventory is None:
            raise RuntimeError("Failed to find `Inventory` argument.")

        if not inventory.repo.git.is_clean_worktree():
            raise OnyoRepoError("Git worktree is not clean.")
        if inventory.operations_pending():
            raise PendingInventoryOperationError(
                f"Inventory at {inventory.root} has pending operations.")
        return func(*args, **kwargs)
    return wrapper


def fsck(repo: OnyoRepo,
         tests: list[str] | None = None) -> None:
    r"""Run a suite of checks to verify the integrity and validity of an Onyo
    repository and its contents.

    By default, the following tests will be performed:

    * ``clean-tree``: verify that git has no changed (staged or unstaged) or
      untracked files
    * ``anchors``: verify that all directories (outside of .onyo) have an
      .anchor file
    * ``asset-unique``: verify that all asset names are unique
    * ``asset-yaml``: verify that all asset contents are valid YAML

    Parameters
    ----------
    repo
        The Repository on which to perform the fsck on.

    tests
        A list with the names of tests to perform. By default, all tests are
        performed on the repository.

    Raises
    ------
    ValueError
        If a test is specified that does not exist.

    OnyoInvalidRepoError
        If a test fails.
    """

    from functools import partial
    from onyo.lib.utils import has_unique_names, validate_yaml

    all_tests = {
        # TODO: fsck would probably want to relay or analyze `git-status` output, rather
        # than just get a bool for clean worktree:
        "clean-tree": repo.git.is_clean_worktree,
        "anchors": repo.validate_anchors,
        "asset-unique": partial(has_unique_names, repo.asset_paths),
        "asset-yaml": partial(validate_yaml, {repo.git.root / a for a in repo.asset_paths}),
    }
    if tests:
        # only known tests are accepted
        if [x for x in tests if x not in all_tests.keys()]:
            raise ValueError("Invalid test requested. Valid tests are: {}".format(', '.join(all_tests.keys())))
    else:
        tests = list(all_tests.keys())

    # run the selected tests
    for key in tests:
        ui.log(f"'{key}' starting")

        if not all_tests[key]():
            # Note: What's that debug message adding? Alone it lacks the
            #       identifying path and in combination with the exception
            #       it's redundant.
            ui.log_debug(f"'{key}' failed")
            raise OnyoInvalidRepoError(f"'{repo.git.root}' failed fsck test '{key}'")

        ui.log(f"'{key}' succeeded")


@raise_on_inventory_state
def onyo_cat(inventory: Inventory,
             paths: list[Path]) -> None:
    r"""Print the contents of assets.

    At least one valid asset path is required.
    The same paths can be given multiple times.
    If any path specified is invalid, no contents are printed and an error is raised.

    Parameters
    ----------
    inventory
        The inventory containing the assets to print.
    paths
        Path(s) to assets for which to print the contents.

    Raises
    ------
    ValueError
        If paths point to a location which is not an asset, or `paths`
        is empty.

    OnyoInvalidRepoError
        If paths are not valid assets, e.g. because their content is not valid
        YAML format.
    """
    from onyo.lib.utils import validate_yaml
    if not paths:
        raise ValueError("At least one asset path must be specified.")
    non_asset_paths = [str(p) for p in paths if not inventory.repo.is_asset_path(p)]
    if non_asset_paths:
        raise ValueError("The following paths are not asset files:\n%s" %
                         "\n".join(non_asset_paths))
    files = list(p / OnyoRepo.ASSET_DIR_FILE_NAME
                 if inventory.repo.is_asset_dir(p)
                 else p
                 for p in paths)
    # TODO: "Full" asset validation. Address when fsck is reworked
    assets_valid = validate_yaml(deduplicate(files))
    # open file and print to stdout
    for f in files:
        ui.print(f.read_text(), end='')
    if not assets_valid:
        raise OnyoInvalidRepoError("Invalid assets")


@raise_on_inventory_state
def onyo_config(inventory: Inventory,
                config_args: list[str]) -> None:
    r"""Interface the configuration of an onyo repository.

    The config file for the Repo will be identified and the config_args passed
    into a ``git config`` call on the config file.

    Parameters
    ----------
    inventory
        The inventory in question.
    config_args
        The options to be passed to the underlying call of ``git config``.
    """
    from onyo.lib.command_utils import allowed_config_args
    allowed_config_args(config_args)

    subprocess.run(["git", 'config', '-f', str(inventory.repo.ONYO_CONFIG)] +
                   config_args, cwd=inventory.repo.git.root, check=True)

    if not any(a.startswith('--get') or a == '--list' for a in config_args):
        # It's a write operation, and we'd want to commit
        # if there were any changes.
        try:
            inventory.repo.commit(inventory.repo.ONYO_CONFIG,
                                  'config: modify repository config')
        except subprocess.CalledProcessError as e:
            if "no changes added to commit" in e.stdout or "nothing to commit" in e.stdout:
                ui.print("No changes to commit.")
                return
            raise


def _edit_asset(inventory: Inventory,
                asset: dict,
                operation: Callable,
                editor: str | None) -> dict:
    r"""Edit `asset` via configured editor and a temporary asset file.

    Utility function for `onyo_edit` and `onyo_new(edit=True)`.
    This is editing a temporary file initialized with `asset`. Once
    the editor is done, `asset` is updated from the file content and
    `operation` is tried in order to validate the content for a
    particular purpose (Currently used: Either `Inventory.add_asset`
    or `Inventory.modify_asset`).
    User is asked to either keep editing or accept the changes
    (if valid).

    Parameters
    ----------
    inventory
      Inventory to edit `asset` for. This is primarily used to check
      whether `operation` resulted in registered operations with that
      inventory in order to remove them, if the edit was not accepted.
    asset
      Asset to edit.
    editor
      Editor to use. This is a to-be executed shell string, that gets
      a path to a temporary file. Defaults to `OnyoRepo.get_editor()`.
    operation
      Function to call with the resulting asset. This function is
      expected to raise, if the edited asset isn't valid for that
      purpose.

    Returns
    -------
    dict
      The edited asset.
    """
    from shlex import quote
    from onyo.lib.consts import RESERVED_KEYS
    from onyo.lib.utils import get_temp_file, get_asset_content

    if not editor:
        editor = inventory.repo.get_editor()

    # Store original reserved keys of `asset`, in order to re-assign
    # them when loading edited file from disc. This is relevant, when
    # `operation` uses them (`Inventory.add_asset`)
    reserved_keys = {k: v for k, v in asset.items() if k in RESERVED_KEYS}

    tmp_path = get_temp_file()
    write_asset_file(tmp_path, asset)

    # For validation of an edited asset, the operation is tried.
    # This is to avoid repeating the same tests (both - code
    # duplication and performance!).
    # However, in order to be able to keep editing even if the
    # operation was valid, a rollback of the changes to the operations
    # queue is required.
    queue_length = len(inventory.operations)
    while True:
        # ### fire up editor
        # Note: shell=True would be needed for a setting like the one used in tests:
        #       EDITOR="printf 'some: thing' >>". Piping needs either shell, or we must
        #       understand what needs piping at the python level here and create several
        #       subprocesses piped together.
        subprocess.run(f'{editor} {quote(str(tmp_path))}', check=True, shell=True)
        operations = None
        try:
            asset = get_asset_content(tmp_path)
            # When reading from file, we don't get reserved keys back, since they are not
            # part of the file content. We do need the object from reading the file to be
            # the basis, though, to get comment roundtrip from ruamel.
            asset.update(reserved_keys)
            operations = operation(asset)
        except NoopError:
            pass  # If edit was a no-op, this is not a ValidationError
        except Exception as e:  # TODO: dedicated type: OnyoValidationError or something # TODO: Ignore NoopError?
            # remove possibly added operations from the queue:
            if queue_length < len(inventory.operations):
                inventory.operations = inventory.operations[:queue_length]
            ui.error(e)
            # TODO: This kind of phrasing the question is bad.
            #       Have a different category of questions in `UI` instead,
            if ui.request_user_response("Cancel command (y) or continue editing asset (n)? "):
                # Error message was already passed to ui. Raise a different exception instead.
                # TODO: Own exception class for that purpose? Can we have no message at all?
                #       -> Make possible in main.py
                raise ValueError("Command canceled.") from e
            else:
                continue
        # ### show diff and ask for confirmation
        if operations:
            ui.print("Effective changes:")
            for op in operations:
                for line in op.diff():
                    ui.print(line)
        if ui.request_user_response("Accept changes? (y/n) "):
            # TODO: We'd want a three-way question: "accept", "skip this asset (discard)" and "continue editing".
            break
        else:
            # remove possibly added operations from the queue:
            if queue_length < len(inventory.operations):
                inventory.operations = inventory.operations[:queue_length]
    tmp_path.unlink()
    return asset


@raise_on_inventory_state
def onyo_edit(inventory: Inventory,
              paths: list[Path],
              message: str | None) -> None:
    r"""Edit the content of assets.

    Parameters
    ----------
    inventory
        The inventory in which to edit assets.

    paths
        The assets to modify.

    message
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    RuntimeError
        If none of the assets specified are valid, e.g. the path does not exist.
    """
    from functools import partial

    # check and set paths
    # Note: This command is an exception. It skips the invalid paths and
    #       proceeds to act upon the valid ones!
    valid_asset_paths = []
    for p in paths:
        if not inventory.repo.is_asset_path(p):
            ui.print(f"\n{p} is not an asset.", file=sys.stderr)
        else:
            valid_asset_paths.append(p)
    if not valid_asset_paths:
        raise RuntimeError("No asset updated.")

    editor = inventory.repo.get_editor()
    for path in valid_asset_paths:
        asset = inventory.get_asset(path)
        _edit_asset(inventory, asset, partial(inventory.modify_asset, path), editor)

    if inventory.operations_pending():
        # TODO: Just like in `new` we don't need to repeat the diffs
        ui.print("Changes:")
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].get("path").relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['modify_assets']]))
                message = inventory.repo.generate_commit_message(
                    format_string="edit [{len}]: {operation_paths}",
                    len=len(operation_paths),
                    operation_paths=operation_paths)
            inventory.commit(message=message)
            return
    ui.print('No assets updated.')


@raise_on_inventory_state
def onyo_get(inventory: Inventory,
             paths: list[Path] | None = None,
             depth: int = 0,
             machine_readable: bool = False,
             match: list[Callable[[dict], bool]] | None = None,
             keys: list[str] | None = None,
             sort: Literal['ascending', 'descending'] = 'ascending') -> list[dict]:
    r"""Query the repository for information about assets.

    Parameters
    ----------
    inventory
      The inventory to query.
    paths
      Limits the query to assets underneath these paths.
      Paths can be assets and directories.
      If no paths are specified, the inventory root is used as default.
    depth
      Number of levels to descend into. Must be greater or equal 0.
      If 0, descend recursively without limit.
    machine_readable
      Whether to print the matching assets as TAB-separated lines,
      where the columns correspond to the `keys`. If `False`,
      print a table meant for human consumption.
    match
      Callables suited for use with builtin `filter`. They are
      passed an asset dictionary and expected to return a `bool`,
      where `True` indicates a match. The result of the query
      consists of all assets that are matched by all callables in
      this list.
    keys
      Defines what key-value pairs of an asset a result is composed of.
      If no `keys` are given the keys then the asset name keys and
      `path` are used.
      Keys may be repeated.
    sort
      How to sort the results by `keys`. Possible values are
      'ascending' and 'descending'. Default: 'ascending'.
      If other values are specified an error is raised.

    Raises
    ------
    ValueError
      On invalid arguments.

    Returns
    -------
    list of dict
      A dictionary per matching asset as defined by `keys`.
    """

    selected_keys = keys.copy() if keys else None

    # TODO: JSON output? Is this done somewhere?
    paths = paths or [inventory.root]

    # validate path arguments
    invalid_paths = set(p
                        for p in paths  # pyre-ignore[16]  `paths` not Optional anymore here
                        if not (inventory.repo.is_inventory_dir(p) or inventory.repo.is_asset_path(p)))
    if invalid_paths:
        err_str = '\n'.join([str(x) for x in invalid_paths])
        raise ValueError(f"The following paths are not part of the inventory:\n{err_str}")

    allowed_sorting = ['ascending', 'descending']
    if sort not in allowed_sorting:
        raise ValueError(f"Allowed sorting modes: {', '.join(allowed_sorting)}")

    selected_keys = selected_keys or inventory.repo.get_asset_name_keys() + ['path']
    results = inventory.get_assets_by_query(paths=paths,
                                            depth=depth,
                                            match=match)
    results = list(fill_unset(results, selected_keys))
    # convert paths for output
    for r in results:
        r['path'] = r['path'].relative_to(inventory.root)

    results = natural_sort(
        assets=results,
        # Note: This intentionally checks for explicitly given `keys`:
        keys=selected_keys if keys else ['path'],
        reverse=sort == 'descending')

    # filter output for `keys` only
    results = [{k: v for k, v in r.items() if k in selected_keys} for r in results]

    if machine_readable:
        sep = '\t'  # column separator
        for data in results:
            values = sep.join([str(data[k]) for k in selected_keys])
            ui.print(f'{values}')
    elif results:
        table = Table(
            box=box.HORIZONTALS, title='', show_header=True,
            header_style='bold')
        for key in selected_keys:
            table.add_column(key, overflow='fold')
        for data in results:
            values = [str(data[k]) for k in selected_keys]
            table.add_row(*values)

        ui.rich_print(table)
    else:
        ui.rich_print('No assets matching the filter(s) were found')
    return results


@raise_on_inventory_state
def onyo_mkdir(inventory: Inventory,
               dirs: list[Path],
               message: str | None) -> None:
    r"""Create new directories in the inventory.

    Intermediate directories will be created as needed (i.e. parent and
    child directories can be created in one call).

    An empty `.anchor` file is added to each directory, to ensure that git
    tracks them even when empty.
    If `dirs` contains duplicates, onyo will create just one new directory and
    ignore the duplicates.

    All paths in `dirs` must be new and valid directory paths inside the
    inventory. However, a path to an existing asset file is valid and means
    to turn that asset file into an asset dir.
    At least one valid path is required.
    If any path specified is invalid no new directories are created, and an
    error is raised.

    Parameters
    ----------
    inventory
        The inventory in which to create new directories.
    dirs
        Paths to directories which to create.
    message
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        If `dirs` is empty.
    """
    if not dirs:
        raise ValueError("At least one directory path must be specified.")
    for d in deduplicate(dirs):  # pyre-ignore[16]  deduplicate would return None only of `dirs` was None.
        # explicit duplicates would make auto-generating message subject more complicated ATM
        inventory.add_directory(d)
    if inventory.operations_pending():
        ui.print('The following directories will be created:')
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['new_directories']]))
                message = inventory.repo.generate_commit_message(
                    format_string="mkdir [{len}]: {operation_paths}",
                    len=len(operation_paths),
                    operation_paths=sorted(operation_paths))
            inventory.commit(message=message)
            return
    ui.print('No directories created.')


def move_asset_or_dir(inventory: Inventory,
                      source: Path,
                      destination: Path) -> None:
    r"""Move a source asset or directory to a destination.

    Parameters
    ----------
    inventory
        Inventory to operate on.
    source
        Path object to an asset or directory which to move to the destination.
    destination
        Path object to an asset or directory to which to move source.
    """
    # TODO: method of Inventory?
    try:
        inventory.move_asset(source, destination)
    except NotAnAssetError:
        inventory.move_directory(source, destination)


def _maybe_rename(inventory: Inventory,
                  src: Path,
                  dst: Path) -> None:
    r"""Helper for `onyo_mv`"""

    try:
        inventory.rename_directory(src, dst)
    except NotADirError as e:
        # We tried to rename an asset dir.
        inventory.reset()
        raise ValueError("Renaming an asset requires the 'set' command.") from e


@raise_on_inventory_state
def onyo_mv(inventory: Inventory,
            source: list[Path] | Path,
            destination: Path,
            message: str | None = None) -> None:
    r"""Move assets or directories, or rename a directory.

    If `destination` is an asset file, turns it into an asset dir first.

    Parameters
    ----------
    inventory
        The Inventory in which to move assets or directories.

    source
        A list of source paths that will be moved to the destination.
        If a single source directory is given and the destination is a
        non-existing directory, the source will be renamed.

    destination
        The path to which the source(s) will be moved, or a single
        source directory will be renamed.

    message
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        If multiple source paths are specified to be renamed.
    """
    sources = [source] if not isinstance(source, list) else source

    # If destination exists, it as to be an inventory directory and we are dealing with a move.
    # If it doesn't exist at all, we are dealing with a rename of a dir.
    # Special case: One source and its name is explicitly restated as the destination. This is a move, too.
    # TODO: Error reporting. Right now we just let the first exception from inventory operations bubble up.
    #       We could catch them and collect all errors (use ExceptionGroup?)
    if destination.exists():
        # MOVE
        subject = "mv"
        if not inventory.repo.is_inventory_dir(destination) \
                and inventory.repo.is_asset_path(destination):
            # destination is an existing asset; turn into asset dir
            inventory.add_directory(destination)
        for s in sources:
            move_asset_or_dir(inventory, s, destination)
    elif len(sources) == 1 and destination.name == sources[0].name:
        # MOVE special case
        subject = "mv"
        move_asset_or_dir(inventory, sources[0], destination.parent)
    elif len(sources) == 1 and sources[0].is_dir() and destination.parent.is_dir():  # TODO: last condition necessary?
        # RENAME directory
        subject = "ren"
        if sources[0].parent != destination.parent:
            # This is a `mv` into non-existent dir not under same parent.
            # Hence, first move and only then rename.
            subject = "mv + " + subject
            inventory.move_directory(sources[0], destination.parent)
            _maybe_rename(inventory, destination.parent / sources[0].name, destination)
            # TODO: Replace - see issue #546:
            inventory._ignore_for_commit.append(destination.parent / sources[0].name)
        else:
            _maybe_rename(inventory, sources[0], destination)
    else:
        raise ValueError("Can only move into an existing directory/asset, or rename a single directory.")

    if inventory.operations_pending():
        ui.print("The following will be {}:".format("moved" if subject == "mv" else "renamed"))
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['rename_assets'] or
                    op.operator == OPERATIONS_MAPPING['move_assets'] or
                    op.operator == OPERATIONS_MAPPING['move_directories'] or
                    op.operator == OPERATIONS_MAPPING['rename_directories']]))
                message = inventory.repo.generate_commit_message(
                    format_string="{prefix} [{len}]: {operation_paths} -> {destination}",
                    prefix=subject,
                    len=len(operation_paths),
                    operation_paths=operation_paths,
                    destination=destination.relative_to(inventory.root))
            inventory.commit(message=message)
            return
    ui.print('Nothing was moved.')


@raise_on_inventory_state
def onyo_new(inventory: Inventory,
             directory: Path | None = None,
             template: str | None = None,
             clone: Path | None = None,
             tsv: Path | None = None,
             keys: list[Dict[str, str | int | float]] | None = None,
             edit: bool = False,
             message: str | None = None) -> None:
    r"""Create new assets and add them to the inventory.

    Either keys, tsv or edit must be given.
    If keys and tsv and keys define multiple assets: Number of assets must match.
    If only one value pair key: Update tsv assets with them.
    If `keys` and tsv conflict: raise, there's no priority overwriting or something.
    --directory and `directory` reserved key given -> raise, no priority
    pseudo-keys must not be given -> PSEUDO_KEYS

    TODO: Document special keys (directory, asset dir, template, etc) -> RESERVED_KEYS
    TODO: 'directory' -> relative to inventory root!

    - keys vs template: fill up? Write it down!
    - edit: TODO: May lead to delay any error until we got the edit result? As in: Can start empty?
    - template: if it can be given as a key, do we need a dedicated option?

    # TODO: This just copy pasta from StoreKeyValuePair, ATM. To some extend should go into help for `--key`.
    # But: description of TSV and special keys required.
    Every key appearing multiple times in `key=value` is applied to a new dictionary every time.
    All keys appearing multiple times, must appear the same number of times (and thereby define the number of dicts
    to be created). In case of different counts: raise.
    Every key appearing once in `key_values` will be applied to all dictionaries.

    Parameters
    ----------
    inventory
        The Inventory in which to create new assets.

    directory
        The directory to create new asset(s) in. Defaults to CWD.
        Note, that it technically is not a default (as per signature of this
        function), because we need to be able to tell whether a path was given
        in order to check for conflict with a possible 'directory' key or
        table column.

    template
        The name of a template file in ``.onyo/templates/`` that is copied as a
        base for the new assets to be created.

    clone
        Path to an asset to clone. Mutually exclusive with `template`.
        Note, that a straight clone with no change via `keys`, `tsv` or `edit`
        would result in the exact same asset, which therefore is bound to fail.

    tsv
        A path to a tsv table that describes new assets to be created.

    keys
        List of dictionaries with key/value pairs that will be set in the newly
        created assets. The keys used in the ``onyo.assets.filename`` config
        ``.onyo/config`` (e.g. ``filename = "{type}_{make}_{model}.{serial}"``)
        are used in the asset name and therefore a required.

    edit
        If True, newly created assets are opened in the editor before the
        changes are saved.

    message
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        If information is invalid, missing, or contradictory.
    """
    from onyo.lib.consts import PSEUDO_KEYS
    from copy import deepcopy

    keys = keys or []
    if not tsv and not keys and not edit:
        raise ValueError("Either key-value pairs or a tsv file must be given.")
    if template and clone:
        raise ValueError("'template' and 'clone' options are mutually exclusive.")
    # Try to get editor early in case it's bound to fail;
    # Empty string b/c pyre doesn't properly consider the condition and complains
    # when we pass `editor` where it's not optional.
    editor = inventory.repo.get_editor() if edit else ""

    # read and verify the information for new assets from TSV
    tsv_dicts = None
    if tsv:
        import csv
        with tsv.open('r', newline='') as tsv_file:
            reader = csv.DictReader(tsv_file, delimiter='\t')
            if reader.fieldnames is None:
                raise ValueError(f"No header fields in tsv {str(tsv)}")
            if template and 'template' in reader.fieldnames:
                raise ValueError("Can't use '--template' option and 'template' column in tsv.")
            if clone and 'template' in reader.fieldnames:
                raise ValueError("Can't use '--clone' option and 'template' column in tsv.")
            if directory and 'directory' in reader.fieldnames:
                raise ValueError("Can't use '--directory' option and 'directory' column in tsv.")
            tsv_dicts = [row for row in reader]
            # Any line's remainder (values beyond available columns) would be stored in the `None` key.
            # Note, that `i` is shifted by one in order to give the correct line number (header line + index of dict):
            for d, i in zip(tsv_dicts, range(1, len(tsv_dicts) + 1)):
                if None in d.keys() and d[None] != ['']:
                    raise ValueError(f"Values exceed number of columns in {str(tsv)} at line {i}: {d[None]}")

    if tsv_dicts and len(keys) > 1 and len(keys) != len(tsv_dicts):
        raise ValueError(f"Number of assets in tsv ({len(tsv_dicts)}) doesn't match "
                         f"number of assets given via --keys ({len(keys)}).")

    if tsv_dicts and len(keys) == 1:
        # Fill up to number of assets
        keys = [keys[0] for i in range(len(tsv_dicts))]

    if tsv_dicts and keys:
        # merge both to get the actual asset specification
        duplicate_keys = set(tsv_dicts[0].keys()).intersection(set(keys[0].keys()))
        if duplicate_keys:
            # TODO: We could list the entire asset (including duplicate key-values) to better identify where the
            # problem is.
            raise ValueError(f"Asset keys specified twice: {duplicate_keys}")
        [tsv_dicts[i].update(keys[i]) for i in range(len(tsv_dicts))]
        specs = tsv_dicts
    else:
        # We have either keys given or a TSV, not both. Note, however, that neither one could be given
        # (plain edit-based onyo_new). In this case we get `keys` default into `specs` here, which should be an empty
        # list, thus preventing any iteration further down the road.
        specs = tsv_dicts if tsv_dicts else deepcopy(keys)  # we don't want to change the caller's `keys` dictionaries

    # TODO: These validations could probably be more efficient and neat.
    #       For ex., only first dict is actually relevant. It's either TSV (columns exist for all) or came from --key,
    #       where everything after the first one comes from repetition (However, what about python interface where one
    #       could pass an arbitrary list of dicts? -> requires consistency check like TSV + doc).
    if any('directory' in d.keys() for d in specs):
        if directory:
            raise ValueError("Can't use '--directory' option and specify 'directory' key.")
    else:
        # default
        directory = directory or Path.cwd()
    if template and any('template' in d.keys() for d in specs):
        raise ValueError("Can't use 'template' key and 'template' option.")
    if clone and any('template' in d.keys() for d in specs):
        raise ValueError("Can't use 'clone' key and 'template' option.")

    for pseudo_key in PSEUDO_KEYS:
        for d in specs:
            if pseudo_key in d.keys():
                raise ValueError(f"Pseudo key '{pseudo_key}' must not be specified.")

    # Generate actual assets:
    if edit and not specs:
        # Special case: No asset specification defined via `keys` or `tsv`, but we have `edit`.
        # This implies a single asset, starting with a (possibly empty) template.
        specs = [{}]

    for spec in specs:
        # 1. Unify directory specification
        directory = Path(spec.get('directory', directory))
        if not directory.is_absolute():
            directory = inventory.root / directory
        spec['directory'] = directory
        # 2. start from template
        if clone:
            asset = inventory.get_asset(clone)
            asset.pop('path')
        else:
            asset = inventory.get_asset_from_template(spec.pop('template', None) or template)
        # 3. fill in asset specification
        asset.update(spec)
        # 4. (try to) add to inventory
        if edit:
            _edit_asset(inventory, asset, inventory.add_asset, editor)
        else:
            inventory.add_asset(asset)

    if inventory.operations_pending():
        if not edit:
            # Note: If `edit` was given, the diffs where already confirmed per asset.
            #       Don't ask again.
            ui.print("The following will be created:")
            for line in inventory.diff():
                ui.print(line)
        if edit or ui.request_user_response("Create assets? (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].get("path").relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['new_assets']]))
                message = inventory.repo.generate_commit_message(
                    format_string="new [{len}]: {operation_paths}",
                    len=len(operation_paths),
                    operation_paths=operation_paths)
            inventory.commit(message=message)
            return
    ui.print('No new assets created.')


@raise_on_inventory_state
def onyo_rm(inventory: Inventory,
            paths: list[Path] | Path,
            message: str | None,
            mode: Literal["asset", "dir", "all"] = "all") -> None:
    r"""Delete assets and/or directories from the inventory.

    Parameters
    ----------
    inventory
        The inventory in which assets and/or directories will be deleted.

    paths
        List of paths to assets and/or directories to delete from the Inventory.
        If any path given is not valid, none of them gets deleted.

    mode
        One of 'asset', 'dir', or 'all'.
        In mode 'all' any given path is removed (recursively).
        In mode 'asset' only paths to assets are accepted. If an asset
        is in fact an asset dir, this removes the asset aspect of it only,
        leaving behind a regular inventory dir.
        In mode 'dir' only paths to dirs are accepted. If a dir happens to
        be an asset dir, this removes the dir aspect from it, turning it
        into a regular asset file.

    message
        An optional string to overwrite Onyo's default commit message.
    """
    paths = [paths] if not isinstance(paths, list) else paths

    if mode == "all":
        for p in paths:
            try:
                inventory.remove_asset(p)
                is_asset = True
            except NotAnAssetError:
                is_asset = False
            if not is_asset or inventory.repo.is_asset_dir(p):
                inventory.remove_directory(p)
    elif mode == "asset":
        invalid_paths = [str(p) for p in paths if not inventory.repo.is_asset_path(p)]
        if invalid_paths:
            raise ValueError("The following paths aren't assets:\n%s" %
                             "\n".join(invalid_paths))
        for p in paths:
            inventory.remove_asset(p)
    elif mode == "dir":
        invalid_paths = [str(p) for p in paths if not inventory.repo.is_inventory_dir(p)]
        if invalid_paths:
            raise ValueError("The following paths aren't inventory directories:\n%s" %
                             "\n".join(invalid_paths))
        for p in paths:
            inventory.remove_directory(p)

    if inventory.operations_pending():
        ui.print('The following will be deleted:')
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['remove_assets'] or
                    op.operator == OPERATIONS_MAPPING['remove_directories']]))
                message = inventory.repo.generate_commit_message(
                    format_string="rm [{len}]: {operation_paths}",
                    len=len(operation_paths),
                    operation_paths=operation_paths)
            inventory.commit(message)
            return
    ui.print('Nothing was deleted.')


@raise_on_inventory_state
def onyo_set(inventory: Inventory,
             keys: Dict[str, str | int | float],
             assets: list[Path],
             rename: bool = False,
             message: str | None = None) -> str | None:
    r"""Set key-value pairs of assets, and change asset names.

    Parameters
    ----------
    inventory
        The Inventory in which to set key/values for assets.
    assets
        Paths to assets for which to set key-value pairs.
    keys
        Key-value pairs that will be set in assets. If keys already exist in an
        asset their value will be overwritten, if they do not exist the values
        are added.
        If keys are specified which appear in asset names the rename option is
        needed and changes the file names.
        The key 'is_asset_directory' (bool) can be used to change whether an
        asset is an asset directory.
    rename
        Whether to allow changing of keys that are part of the asset name.
        If False, such a change raises a `ValueError`.
    message
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        If a given path is invalid or changes are made that would result in
        renaming an asset, while `rename` is not true, or if `keys` is empty.
    """
    if not assets:
        raise ValueError("At least one asset must be specified.")
    if not keys:
        raise ValueError("At least one key-value pair must be specified.")
    if any(not k or not k.strip() for k in keys.keys()):
        raise ValueError("Keys are not allowed to be empty or None-values.")
    if not rename and any(k in inventory.repo.get_asset_name_keys() for k in keys.keys()):
        raise ValueError("Can't change asset name keys without --rename.")

    # TODO: Remove is_asset_directory from RESERVED_KEYS altogether?
    disallowed_keys = RESERVED_KEYS + PSEUDO_KEYS
    disallowed_keys.remove("is_asset_directory")
    if any(k in disallowed_keys for k in keys.keys()):
        raise ValueError(f"Can't set any of the keys ({', '.join(disallowed_keys)}).")

    non_asset_paths = [str(a) for a in assets if not inventory.repo.is_asset_path(a)]
    if non_asset_paths:
        raise ValueError("The following paths aren't assets:\n%s" %
                         "\n".join(non_asset_paths))

    for asset in [inventory.get_asset(a) for a in assets]:
        new_content = copy.deepcopy(asset)
        new_content.update(keys)
        for k in PSEUDO_KEYS:
            new_content.pop(k)
        try:
            inventory.modify_asset(asset, new_content)
        except NoopError:
            pass

    if inventory.operations_pending():
        # display changes
        ui.print("The following assets will be changed:")
        for line in inventory.diff():
            ui.print(line)

        if ui.request_user_response("Update assets? (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].get("path").relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['modify_assets']]))
                message = inventory.repo.generate_commit_message(
                    format_string="set [{len}] ({keys}): {operation_paths}",
                    len=len(operation_paths),
                    keys=list(keys.keys()),
                    operation_paths=operation_paths)
            inventory.commit(message=message)
            return
    ui.print("No assets updated.")


@raise_on_inventory_state
def onyo_tree(inventory: Inventory,
              dirs: list[tuple[str, Path]]) -> None:
    r"""Print the directory tree of paths.

    Parameters
    ----------
    inventory
        The inventory in which the directories to display are located.

    dirs
        A list of tuples containing (str, Path) of directories to build a tree
        of.

        The description is used as a text representation of what path the user
        requested. This way, regardless of how the user requested a path
        (relative, absolute, subdir, etc), it is always printed "correctly".

    Raises
    ------
    ValueError
        If paths are invalid.
    """
    # sanitize the paths
    non_inventory_dirs = [desc for (desc, p) in dirs if not inventory.repo.is_inventory_dir(p)]
    if non_inventory_dirs:
        raise ValueError("The following paths are not inventory directories: %s" %
                         '\n'.join(non_inventory_dirs))

    for (desc, p) in dirs:
        ui.rich_print(f'[bold][sandy_brown]{desc}[/sandy_brown][/bold]')
        for line in _tree(p):
            ui.rich_print(line)


def _tree(dir_path: Path, prefix: str = '') -> Generator[str, None, None]:
    r"""Yield lines that assemble tree-like output, stylized by rich.

    Parameters
    ----------
    dir_path
        Path of directory to yield tree of.
    prefix
        Lines should be prefixed with this string. In practice, only useful by
        ``_tree`` itself recursing into directories.
    """
    space = '    '
    pipe =  '│   '  # noqa: E222
    tee =   '├── '  # noqa: E222
    last =  '└── '  # noqa: E222

    # get and sort the children
    children = sorted(list(dir_path.iterdir()))
    for path in children:
        # ignore hidden files/dirs
        if path.name[0] == '.':
            continue

        # choose child prefix
        child_prefix = tee  # ├──
        if path == children[-1]:
            child_prefix = last  # └──

        # colorize directories
        path_name = path.name
        if path.is_dir():
            path_name = f'[bold][sandy_brown]{path.name}[/sandy_brown][/bold]'

        yield f'{prefix}{child_prefix}{path_name}'

        # descend into directories
        if path.is_dir():
            next_prefix_level = pipe if child_prefix == tee else space
            yield from _tree(path, prefix=prefix + next_prefix_level)


@raise_on_inventory_state
def onyo_unset(inventory: Inventory,
               keys: list[str],
               assets: list[Path],
               message: str | None = None) -> None:
    r"""Remove keys from assets.

    Parameters
    ----------
    inventory
        The Inventory in which to unset key/values for assets.
    keys
        The keys that will be unset in assets.
        If keys do not exist in an asset, a debug message is logged.
        If keys are specified which appear in asset names an error is raised.
        If `keys` is empty an error is raised.
    assets
        Paths to assets for which to unset key-value pairs.
    message
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        If assets are invalid paths, or `keys` are empty or invalid.

    """
    if not keys:
        raise ValueError("At least one key must be specified.")
    non_asset_paths = [str(a) for a in assets if not inventory.repo.is_asset_path(a)]
    if non_asset_paths:
        raise ValueError("The following paths aren't assets:\n%s" % "\n".join(non_asset_paths))
    if any(k in inventory.repo.get_asset_name_keys() for k in keys):
        raise ValueError("Can't unset asset name keys.")
    if any(k in RESERVED_KEYS + PSEUDO_KEYS for k in keys):
        raise ValueError(f"Can't unset reserved or pseudo keys ({', '.join(RESERVED_KEYS + PSEUDO_KEYS)}).")

    for asset in [inventory.get_asset(a) for a in assets]:
        new_content = copy.deepcopy(asset)
        # remove keys to unset, if they exist
        for key in keys:
            try:
                new_content.pop(key)
            except KeyError:
                ui.log_debug(f"{key} not in {asset}")
        # remove keys illegal to write
        for k in PSEUDO_KEYS:
            new_content.pop(k)
        try:
            inventory.modify_asset(asset, new_content)
        except NoopError:
            pass

    if inventory.operations_pending():
        # display changes
        ui.print("The following assets will be changed:")
        for line in inventory.diff():
            ui.print(line)

        if ui.request_user_response("Update assets? (y/n) "):
            if not message:
                operation_paths = sorted(deduplicate([
                    op.operands[0].get("path").relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING[
                        'modify_assets']]))
                message = inventory.repo.generate_commit_message(
                    format_string="unset [{len}] ({keys}): {operation_paths}",
                    len=len(operation_paths),
                    keys=keys,
                    operation_paths=operation_paths)
            inventory.commit(message=message)
            return
    ui.print("No assets updated.")
