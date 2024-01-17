from __future__ import annotations

import copy
import logging
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

from rich import box
from rich.table import Table

from onyo.lib.command_utils import fill_unset, natural_sort
from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.exceptions import OnyoInvalidRepoError, NotAnAssetError, NoopError
from onyo.lib.inventory import Inventory, OPERATIONS_MAPPING
from onyo.lib.onyo import OnyoRepo
from onyo.lib.ui import ui
from onyo.lib.utils import deduplicate, write_asset_file

log: logging.Logger = logging.getLogger('onyo.commands')


# TODO: For python interface usage, *commands* should probably refuse to do
#       anything if there are pending operations in the inventory.


def fsck(repo: OnyoRepo,
         tests: Optional[list[str]] = None) -> None:
    """Run a suite of checks to verify the integrity and validity of an Onyo
    repository and its contents.

    By default, the following tests will be performed:

    - "clean-tree": verifies that the git tree is clean ---that there are
      no changed (staged or unstaged) nor untracked files.
    - "anchors": verifies that all folders (outside of .onyo) have an
      .anchor file
    - "asset-unique": verifies that all asset names are unique
    - "asset-yaml": loads each assets and checks if it's valid YAML
    - "asset-validity": loads each asset and validates the contents against
      the validation rulesets defined in ``.onyo/validation/``.
    - "pseudo-keys": verifies that assets do not contain pseudo-key names

    Parameters
    ----------
    repo: OnyoRepo
        The Repository on which to perform the fsck on.

    tests: list of str, optional
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
    from .assets import has_unique_names, validate_yaml, validate_assets, contains_no_name_keys

    all_tests = {
        # TODO: fsck would probably want to relay or analyze `git-status` output, rather
        # than just get a bool for clean worktree:
        "clean-tree": repo.git.is_clean_worktree,
        "anchors": repo.validate_anchors,
        "asset-unique": partial(has_unique_names, repo.asset_paths),
        "asset-yaml": partial(validate_yaml, {repo.git.root / a for a in repo.asset_paths}),
        "asset-validity": partial(validate_assets, repo.asset_paths),
        "pseudo-keys": partial(contains_no_name_keys, repo.asset_paths)
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


def onyo_cat(inventory: Inventory,
             paths: list[Path]) -> None:
    """Print the contents of assets.

    At least one valid asset path is required.
    The same paths can be given multiple times.
    If any path specified is invalid, no contents are printed and an error is raised.

    Parameters
    ----------
    inventory: Inventory
        The inventory containing the assets to print.
    paths: list of Path
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
    from .assets import validate_yaml
    if not paths:
        raise ValueError("At least one asset path must be specified.")
    non_asset_paths = [str(p) for p in paths if not inventory.repo.is_asset_path(p)]
    if non_asset_paths:
        raise ValueError("The following paths are not asset files:\n%s" %
                         "\n".join(non_asset_paths))
    # TODO: "Full" asset validation. Address when fsck is reworked
    assets_valid = validate_yaml(set(paths))
    # open file and print to stdout
    for path in paths:
        # TODO: Probably better to simply print
        #       `dict_to_yaml(inventory.repo.get_asset_content(path))` - no need to
        #       distinguish asset and asset dir at this level. However, need to
        #       make sure to not print pointless empty lines.
        f = path / OnyoRepo.ASSET_DIR_FILE_NAME if inventory.repo.is_asset_dir(path) else path
        ui.print(f.read_text(), end='')
    if not assets_valid:
        raise OnyoInvalidRepoError("Invalid assets")


def onyo_config(inventory: Inventory,
                config_args: list[str]) -> None:
    """Interface the configuration of an onyo repository.

    The config file for the Repo will be identified and the config_args passed
    into a ``git config`` call on the config file.

    Parameters
    ----------
    inventory: Inventory
        The inventory in question.
    config_args: list of str
        The options to be passed to the underlying call of ``git config``.
    """
    from onyo.lib.command_utils import sanitize_args_config
    git_config_args = sanitize_args_config(config_args)

    subprocess.run(["git", 'config', '-f', str(inventory.repo.ONYO_CONFIG)] +
                   git_config_args, cwd=inventory.repo.git.root, check=True)

    if not any(a.startswith('--get') or a == '--list' for a in git_config_args):
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
                editor: Optional[str]) -> dict:
    """Edit `asset` via configured editor and a temporary asset file.

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
    inventory: Inventory
      Inventory to edit `asset` for. This is primarily used to check
      whether `operation` resulted in registered operations with that
      inventory in order to remove them, if the edit was not accepted.
    asset: dict
      Asset to edit.
    editor: string, optional
      Editor to use. This is a to-be executed shell string, that gets
      a path to a temporary file. Defaults to `OnyoRepo.get_editor()`.
    operation: Callable
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


def onyo_edit(inventory: Inventory,
              paths: list[Path],
              message: Optional[str]) -> None:
    """Edit the content of assets.

    Parameters
    ----------
    inventory: Inventory
        The inventory in which to edit assets.

    paths: Path or list of Path
        The assets to modify.

    message: str, optional
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


def onyo_get(inventory: Inventory,
             paths: Optional[list[Path]],
             depth: int,
             machine_readable: bool,
             match: Optional[list[Callable[[dict], bool]]],
             keys: Optional[list[str]],
             sort: str = 'ascending') -> list[dict]:
    """Query the repository for assets.

    Parameters
    ----------
    inventory: Inventory
      The inventory to query.
    paths: list of Path, optional
      Limits the query to assets underneath these paths.
    depth: int
      Number of levels to descent into. Must be greater or equal 0.
      If 0, descend recursively without limit.
    machine_readable: bool
      Whether to print the matching assets as TAB-separated lines,
      where the columns correspond to the `keys`. If `False`,
      print a table meant for human consumption.
    match: list of Callable
      Callables suited for use with builtin `filter`. They are
      passed an asset dictionary and expected to return a `bool`,
      where `True` indicates a match. The result of the query
      consists of all assets that are matched by all callables in
      this list.
    keys: list of str
      Defines what key-value pairs of an asset a result is composed of.
      If no `keys` are given the keys then the asset name keys are
      used. The 'path' pseudo-key is always appended.
      Keys may be repeated.
    sort: str
      How to sort the results by `keys`. Possible values are
      'ascending' and 'descending'. Default: 'ascending'.

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

    selected_keys = selected_keys or inventory.repo.get_asset_name_keys()
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

    # for now, always include path to match previous behavior:
    # TODO: Should we hardcode 'path' here?
    if 'path' not in selected_keys:
        selected_keys.append('path')
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
            table.add_column(key, no_wrap=True)
        for data in results:
            values = [str(data[k]) for k in selected_keys]
            table.add_row(*values)

        ui.rich_print(table)
    else:
        ui.rich_print('No assets matching the filter(s) were found')
    return results


def onyo_mkdir(inventory: Inventory,
               dirs: list[Path],
               message: Optional[str]) -> None:
    """Create new directories in the inventory.

    Parameters
    ----------
    inventory: Inventory
        The inventory in which to create new directories.

    dirs: list of Path
        Paths to directories which to create.

    message: str, optional
        An optional string to overwrite Onyo's default commit message.
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
    """Move a source asset or directory to a destination.

    Parameters
    ----------
    source: Path
        Path object to an asset or directory which to move to the destination.

    destination: Path
        Path object to an asset or directory to which to move source.
    """
    # TODO: method of Inventory?
    try:
        inventory.move_asset(source, destination)
    except NotAnAssetError:
        inventory.move_directory(source, destination)


def onyo_mv(inventory: Inventory,
            source: list[Path] | Path,
            destination: Path,
            message: Optional[str] = None) -> None:
    """Move assets or directories, or rename a directory.

    Parameters
    ----------
    inventory: Inventory
        The Inventory in which to move assets or directories.

    source: Path or list of Path
        A list of source paths that will be moved to the destination.
        If a single source directory is given and the destination is a
        non-existing directory, the source will be renamed.

    destination: Path
        The path to which the source(s) will be moved, or a single
        source directory will be renamed.

    message: str, optional
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
    if len(sources) == 1 and destination.name == sources[0].name:
        # MOVE special case
        subject = "mv"
        move_asset_or_dir(inventory, sources[0], destination.parent)
    elif destination.exists():
        # MOVE
        subject = "mv"
        for s in sources:
            move_asset_or_dir(inventory, s, destination)
    elif len(sources) == 1 and sources[0].is_dir() and destination.parent.is_dir():
        # RENAME directory
        subject = "ren"
        inventory.rename_directory(sources[0], destination)
    else:
        raise ValueError("Can only move into an existing directory or rename a single directory.")

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


def onyo_new(inventory: Inventory,
             path: Optional[Path] = None,
             template: Optional[str] = None,
             tsv: Optional[Path] = None,
             keys: Optional[list[Dict[str, str]]] = None,
             edit: bool = False,
             message: Optional[str] = None) -> None:
    """Create new assets and add them to the inventory.

    Either keys, tsv or edit must be given.
    If keys and tsv and keys define multiple assets: Number of assets must match.
    If only one value pair key: Update tsv assets with them.
    If `keys` and tsv conflict: raise, there's no priority overwriting or something.
    --path and `directory` reserved key given -> raise, no priority
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
    inventory: Inventory
        The Inventory in which to create new assets.

    path: Path, optional
        The directory to create new asset(s) in. Defaults to CWD.
        Note, that it technically is not a default (as per signature of this
        function), because we need to be able to tell whether a path was given
        in order to check for conflict with a possible 'directory' key or
        table column.

    template: str, optional
        The name of a template file in ``.onyo/templates/`` that is copied as a
        base for the new assets to be created.

    tsv: Path, optional
        A path to a tsv table that describes new assets to be created.

    keys: list of dict of str, optional
        List of dictionaries with key/value pairs that will be set in the newly
        created assets. The keys used in the ``onyo.assets.filename`` config
        ``.onyo/config`` (e.g. ``filename = "{type}_{make}_{model}.{serial}"``)
        are used in the asset name and therefore a required.

    edit: bool
        If True, newly created assets are opened in the editor before the
        changes are saved.

    message: str, optional
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
            if path and 'directory' in reader.fieldnames:
                raise ValueError("Can't use '--path' option and 'directory' column in tsv.")
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
        if path:
            raise ValueError("Can't use '--path' option and specify 'directory' key.")
    else:
        # default
        path = path or Path.cwd()

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
        directory = Path(spec.get('directory', path))
        if not directory.is_absolute():
            directory = inventory.root / directory
        spec['directory'] = directory
        # 2. start from template
        template_name = spec.pop('template', None) or template
        asset = inventory.get_asset_from_template(template_name)
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


def onyo_rm(inventory: Inventory,
            paths: list[Path] | Path,
            message: Optional[str]) -> None:
    """Delete assets and/or directories from the inventory.

    Parameters
    ----------
    inventory: Inventory
        The inventory in which assets and/or directories will be deleted.

    paths: Path or list of Path
        List of paths to assets and/or directories to delete from the Inventory.
        If any path given is not valid, none of them gets deleted.

    message: str, optional
        An optional string to overwrite Onyo's default commit message.
    """
    paths = [paths] if not isinstance(paths, list) else paths

    for p in paths:
        try:
            inventory.remove_asset(p)
            is_asset = True
        except NotAnAssetError:
            is_asset = False
        if not is_asset or inventory.repo.is_asset_dir(p):
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


def onyo_set(inventory: Inventory,
             keys: Dict[str, str | int | float],
             paths: Optional[list[Path]] = None,
             match: Optional[list[Callable[[dict], bool]]] = None,
             rename: bool = False,
             depth: int = 0,
             message: Optional[str] = None) -> Optional[str]:
    """Set key-value pairs of assets, and change asset names.

    Parameters
    ----------
    inventory: Inventory
        The Inventory in which to set key/values for assets.
    paths: Path or list of Path, optional
        Paths to assets or directories for which to set key-value pairs.
        If paths are directories, the values will be set recursively in assets
        under the specified path.
        If no paths are specified, CWD is used as default.
    keys: dict
        Key-value pairs that will be set in assets. If keys already exist in an
        asset their value will be overwritten, if they do not exist the values
        are added.
        If keys are specified which appear in asset names the rename option is
        needed and changes the file names.
    match: list of Callable, optional
        TODO: Understand filtering. This might still be refactored.
    rename: bool
        Whether to allow changing of keys that are part of the asset name.
        If False, such a change raises a `ValueError`.
    depth: int
        Depth limit of recursion if a `path` is a directory.
        0 means no limit and is the default.
    message: str, optional
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        If a given path is invalid or changes are made that would result in
        renaming an asset, while `rename` is not true.
    """
    paths = paths or []
    if not keys:
        raise ValueError("At least one key-value pair must be specified.")

    if not rename and any(k in inventory.repo.get_asset_name_keys() for k in keys.keys()):
        raise ValueError("Can't change asset name keys without --rename.")
    if any(k in RESERVED_KEYS for k in keys.keys()):
        raise ValueError(f"Can't set reserved keys ({', '.join(RESERVED_KEYS)}).")

    non_inventory_paths = [str(p)
                           for p in paths
                           if not inventory.repo.is_asset_path(p) and
                           not inventory.repo.is_inventory_dir(p)]
    if non_inventory_paths:
        raise ValueError("The following paths are neither an inventory directory nor an asset:\n%s" %
                         "\n".join(non_inventory_paths))
    assets = inventory.get_assets_by_query(paths=paths,
                                           depth=depth,
                                           match=match)

    for asset in assets:
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


def onyo_tree(inventory: Inventory,
              paths: list[Path] = []) -> None:
    """Print the directory tree of paths.

    Parameters
    ----------
    inventory: Inventory
        The inventory in which the directories to display are located.

    paths: list of Path
        The paths to directories for which to print the directory tree.
        If no path is specified, `onyo_tree(inventory)` prints the
        directory tree for the root of the inventory.

    Raises
    ------
    ValueError
        If paths are invalid.
    """
    # sanitize the paths
    paths = paths if paths else [inventory.root]
    non_inventory_dirs = [str(p) for p in paths if not inventory.repo.is_inventory_dir(p)]
    if non_inventory_dirs:
        raise ValueError("The following paths are not inventory directories: %s" %
                         '\n'.join(non_inventory_dirs))

    # run it
    ret = subprocess.run(
        ['tree', *map(str, paths)], capture_output=True, text=True, check=True)
    # print tree output
    ui.print(ret.stdout)


def onyo_unset(inventory: Inventory,
               keys: list[str],
               match: Optional[list[Callable[[dict], bool]]],
               paths: Optional[list[Path]] = None,
               depth: int = 0,
               message: Optional[str] = None) -> None:
    """Remove keys from assets.

    Parameters
    ----------
    inventory: Inventory
        The Inventory in which to unset key/values for assets.
    keys: list
        The keys that will be unset in assets.
        If keys do not exist in an asset, a debug message is logged.
        If keys are specified which appear in asset names an error is raised.
    match: list of Callable, optional
      Callables suited for use with builtin `filter`. They are
      passed an asset dictionary and expected to return a `bool`,
      where `True` indicates a match. `keys` will be removed from
      all assets that are matched by all callables in this list.
    paths: Path or list of Path, optional
        Paths to assets or directories for which to unset key-value pairs.
        If paths are directories, the values will be unset recursively in assets
        under the specified path.
        If no paths are specified, CWD is used as default.
    depth: int
        Depth limit of recursion if a `path` is a directory.
        0 means no limit and is the default.
    message: str, optional
        An optional string to overwrite Onyo's default commit message.
    """
    paths = paths or []

    non_inventory_paths = [str(p) for p in paths
                           if not inventory.repo.is_asset_path(p) and
                           not inventory.repo.is_inventory_dir(p)]

    if non_inventory_paths:
        raise ValueError("The following paths are neither an inventory directory nor an ",
                         "asset:\n%s" % "\n".join(non_inventory_paths))

    if any(k in inventory.repo.get_asset_name_keys() for k in keys):
        raise ValueError("Can't unset asset name keys.")
    if any(k in RESERVED_KEYS for k in keys):
        raise ValueError(f"Can't unset reserved keys ({', '.join(RESERVED_KEYS)}).")

    asset_paths_to_unset = inventory.get_assets_by_query(paths=paths,
                                                         depth=depth,
                                                         match=match)

    for asset in asset_paths_to_unset:
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
