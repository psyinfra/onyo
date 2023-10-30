from __future__ import annotations

import subprocess
import sys
import logging
from typing import Dict, Iterable, Optional
from pathlib import Path

from rich.console import Console
from rich import box
from rich.table import Table

from onyo.lib.ui import ui
from onyo.lib.inventory import Inventory, OPERATIONS_MAPPING
from onyo.lib.assets import PSEUDO_KEYS, get_assets_by_query
from onyo.lib.command_utils import sanitize_keys, set_filters, \
    fill_unset, natural_sort
from onyo.lib.exceptions import OnyoInvalidRepoError, NotAnAssetError, NoopError
from onyo.lib.filters import UNSET_VALUE
from onyo.lib.onyo import OnyoRepo
from onyo.lib.utils import edit_asset, deduplicate

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
    from .assets import has_unique_names, validate_yaml, validate_assets, contains_no_pseudo_keys

    all_tests = {
        "clean-tree": repo.git.is_clean_worktree,
        "anchors": repo.validate_anchors,
        "asset-unique": partial(has_unique_names, repo.asset_paths),
        "asset-yaml": partial(validate_yaml, {repo.git.root / a for a in repo.asset_paths}),
        "asset-validity": partial(validate_assets, repo.asset_paths),
        "pseudo-keys": partial(contains_no_pseudo_keys, repo.asset_paths)
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


def onyo_cat(repo: OnyoRepo,
             paths: Iterable[Path]) -> None:
    """Print the contents of assets.

    Parameters
    ----------
    repo: OnyoRepo
        The Onyo Repository containing the assets to print.

    paths: Path or Iterable of Path
        Path(s) to assets for which to print the contents.

    Raises
    ------
    ValueError
        If paths point to a location which is not an asset.

    OnyoInvalidRepoError
        If paths are not valid assets, e.g. because their content is not valid
        YAML format.
    """
    from .assets import validate_yaml
    non_asset_paths = [str(p) for p in paths if not repo.is_asset_path(p)]
    if non_asset_paths:
        raise ValueError("The following paths are not asset files:\n%s",
                         "\n".join(non_asset_paths))
    # TODO: "Full" asset validation. Address when fsck is reworked
    assets_valid = validate_yaml(set(paths))
    # open file and print to stdout
    for path in paths:
        # TODO: Probably better to simply print
        #       `dict_to_yaml(repo.get_asset_content(path))` - no need to
        #       distinguish asset and asset dir at this level. However, need to
        #       make sure to not print pointless empty lines.
        f = path / OnyoRepo.ASSET_DIR_FILE if repo.is_asset_dir(path) else path
        ui.print(f.read_text(), end='')
    if not assets_valid:
        raise OnyoInvalidRepoError("Invalid assets")


def onyo_config(repo: OnyoRepo,
                config_args: list[str]) -> None:
    """Interface the configuration of an onyo repository.

    The config file for the Repo will be identified and the config_args passed
    into a ``git config`` call on the config file.

    Parameters
    ----------
    repo: OnyoRepo
        The repository in question.

    config_args: list of str
        The options to be passed to the underlying call of ``git config``.
    """
    from onyo.lib.command_utils import sanitize_args_config
    git_config_args = sanitize_args_config(config_args)

    config_file = repo.dot_onyo / 'config'
    # NOTE: streaming stdout and stderr directly to the terminal seems to be
    # non-trivial with "subprocess". Here we capture them separately. They
    # won't be interwoven, but will be output to the correct destinations.
    ret = subprocess.run(["git", 'config', '-f', str(config_file)] +
                         git_config_args, cwd=repo.git.root,
                         capture_output=True, text=True, check=True)

    # print any output gathered
    if ret.stdout:
        ui.print(ret.stdout, end='')
    if ret.stderr:
        ui.print(ret.stderr, file=sys.stderr, end='')

    # commit, if there's anything to commit
    if repo.git.files_changed:
        repo.git.stage_and_commit(config_file,
                                  'config: modify repository config')


def onyo_edit(inventory: Inventory,
              asset_paths: Iterable[Path],
              message: Optional[str]) -> None:
    """Edit the content of assets.

    Parameters
    ----------
    inventory: Inventory
        The inventory in which to edit assets.

    asset_paths: Path or Iterable of Path
        The assets to modify.

    message: str, optional
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    RuntimeError
        If none of the assets specified are valid, e.g. the path does not exist.
    """
    from onyo.lib.utils import edit_asset

    # check and set paths
    # Note: This command is an exception. It skips the invalid paths and
    #       proceeds to act upon the valid ones!
    valid_asset_paths = []
    for a in asset_paths:
        if not inventory.repo.is_asset_path(a):
            ui.print(f"\n{a} is not an asset.", file=sys.stderr)
        else:
            valid_asset_paths.append(a)
    if not valid_asset_paths:
        raise RuntimeError("No asset updated.")

    editor = inventory.repo.get_editor()
    for path in valid_asset_paths:
        asset = inventory.get_asset(path)
        modified_asset = edit_asset(asset, editor)
        try:
            inventory.modify_asset(asset, modified_asset)
        except NoopError:
            pass

    if inventory.operations_pending():
        ui.print("Changes:")
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = [
                    op.operands[0].get("path")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['modify_assets']]
                message = inventory.repo.generate_commit_message(
                    cmd="edit",
                    modified=operation_paths)
            inventory.commit(message=message)
            return
    ui.print('No assets updated.')


def get(repo: OnyoRepo,
        sort_ascending: bool,
        sort_descending: bool,
        paths: Optional[list[Path]],
        depth: int,
        machine_readable: bool,
        filter_strings: list[str],
        keys: Optional[list[str]]) -> None:
    """Query the repository to get information from assets.

    Parameters
    ----------
    TODO: command needs refactoring before the full doc-string is possible.

    Raises
    ------
    """
    if sort_ascending and sort_descending:
        msg = ('--sort-ascending (-s) and --sort-descending (-S) cannot be '
               'used together')
        if machine_readable:
            ui.print(msg, file=sys.stderr)
        else:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {msg}')
        raise ValueError

    if not paths:
        paths = [Path.cwd()]

    # validate path arguments
    invalid_paths = set(p for p in paths if not repo.is_inventory_dir(p))
    if invalid_paths:
        err_str = '\n'.join([str(x) for x in invalid_paths])
        raise ValueError(f"The following paths are not part of the inventory:\n{err_str}")
    if not paths:
        raise ValueError("No assets selected.")
    if depth < 0:
        raise ValueError(f"-d, --depth must be 0 or larger, not '{depth}'")

    # TODO: This removes duplicates AND returns pseudo-keys if `keys` is empty. Latter should be done by query.
    #       Former superfluous - it's passed to query as a set anyways.
    keys = sanitize_keys(keys, defaults=PSEUDO_KEYS)

    filters = set_filters(
        filter_strings, repo=repo,
        rich=not machine_readable) if filter_strings else None

    # TODO: This is once more convoluted. path limitation should be its own thing, not integrated in the query
    #       Alternatively: path limiting could become just a filter. Implementation-wise that's easy, once pseudo-keys
    #       are properly delivered by an Asset class and the path pseudo-key is implemented.
    #       - This suggests a generic filter_assets method (for an Inventory)
    #       - Gets filters, possibly arbitrary callables (see filter(callable, list) in get_assets_by_query)
    #       - Check usecases for whether that can cover all the queries
    results = get_assets_by_query(repo.asset_paths,
                                  keys=set(keys),
                                  paths=paths,
                                  depth=depth,
                                  filters=filters)
    # TODO: Move this inside query. A returned asset (-dict) should be filled accordingly already.
    #       See TODO for UNSET_VALUE definition.
    results = fill_unset(results, keys, UNSET_VALUE)

    # TODO: use `natsort` package.
    results = natural_sort(
        assets=list(results),
        keys=keys if sort_ascending or sort_descending else None,
        reverse=True if sort_descending else False)

    if machine_readable:
        sep = '\t'  # column separator
        for asset, data in results:
            values = sep.join([str(value) for value in data.values()])
            ui.print(f'{values}{sep}{asset.relative_to(Path.cwd())}')
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
                table.add_row(*values, str(asset.relative_to(Path.cwd())))

            console.print(table)
        else:
            console.print('No assets matching the filter(s) were found')


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
    for d in deduplicate(dirs):  # explicit duplicates would make auto-generating message subject more complicated ATM
        inventory.add_directory(d)
    if inventory.operations_pending():
        ui.print('The following directories will be created:')
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = [
                    op.operands[0]
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['new_directories']]
                message = inventory.repo.generate_commit_message(
                    cmd="mkdir",
                    modified=operation_paths)
            inventory.commit(message=message)
            return
    ui.print('No directories created.')


def move_asset_or_dir(inventory: Inventory,
                      src: Path,
                      dst: Path) -> None:
    """Move a source asset or directory to a destination.

    Parameters:
    src: Path
        Path object to an asset or directory which to move to the destination.

    dst: Path
        Path object to an asset or directory to which to move source.
    """
    # TODO: method of Inventory?
    try:
        inventory.move_asset(src, dst)
    except NotAnAssetError:
        inventory.move_directory(src, dst)


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
    else:
        # RENAME
        subject = "ren"
        if len(sources) != 1:
            raise ValueError("Cannot rename multiple sources.")
        else:
            inventory.rename_directory(sources[0], destination)

    if inventory.operations_pending():
        ui.print('The following will be moved:')
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if not message:
                operation_paths = [
                    op.operands[0]
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['rename_assets'] or
                    op.operator == OPERATIONS_MAPPING['move_assets'] or
                    op.operator == OPERATIONS_MAPPING['move_directories'] or
                    op.operator == OPERATIONS_MAPPING['rename_directories']]
                message = inventory.repo.generate_commit_message(
                    cmd=subject,
                    destination=destination,
                    modified=operation_paths)
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
    pseudo-keys must not be given -> NEW_PSEUDO_KEYS

    TODO: Document special keys (directory, asset dir, template, etc) -> RESERVED_KEYS

    - keys vs template: fill up? Write it down!
    - edit: TODO: May lead to delay any error until we got the edit result? As in: Can start empty?
    - template: if it can be given as a key, do we need a dedicated option?

    # TODO: This just copy pasta from StoreKeyValuePair, ATM. T some extend should go into help for `--key`.
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
    from onyo.lib.consts import NEW_PSEUDO_KEYS
    from copy import deepcopy

    keys = keys or []
    if not tsv and not keys and not edit:
        # NOTE: edit requires path or directory key!
        # Actually: No. `path` comes with a default (CWD)

        # TODO: Why? We have --edit!  Could even start empty, but certainly from a template.
        #       However, path is required with edit, b/c edit is supposed to edit the file content.
        #       Hence, special keys (like `directory`, asset dir, template, etc.)
        #       can't be set that way. (Although: We could make that work, too)
        # Conclusion: allow for plain edit, but edit only asset file content, not special keys.
        #       path -> default CWD
        raise ValueError("Either key-value pairs or a tsv file must be given.")
    # EDIT needs further validation. We need `directory` key or `path` given. Which sorta implies that this should be
    # done later, after building the specs? -> Actually: No. Path comes with a default.

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
    #       could pass an arbitrary list of dicts?).
    if any('directory' in d.keys() for d in specs):
        if path:
            raise ValueError("Can't use '--path' option and specify 'directory' key.")
    else:
        # default
        path = path or Path.cwd()

    for pseudo_key in NEW_PSEUDO_KEYS:
        for d in specs:
            if pseudo_key in d.keys():
                raise ValueError(f"Pseudo key '{pseudo_key}' must not be specified.")

    # Prepare faux serials
    # TODO: Adjust get_faux_serials to accept num=0 and return empty
    #       Does it save anything to create them bulk?
    #       Only thing seems to be: Easy to check against other just generated ones.
    #       Entire business also makes me wonder about configured fallbacks for naming scheme (triggered by KeyError)
    #       Use case: Us. Serial -> FZJ Inventory number -> faux
    # TODO: This needs to be more generic. Like configure callables to a key? 'serial' -> callable('faux')
    # TODO: Turn the entire replacement into function
    faux_number = sum(1 for d in specs if d.get('serial') == 'faux')
    if faux_number > 0:
        faux_serials = inventory.get_faux_serials(num=faux_number)
        for d in specs:
            if d.get('serial') == 'faux':
                d['serial'] = faux_serials.pop()

    # Generate actual assets:
    if edit and not specs:
        # Special case: No asset specification defined via --keys or --tsv, but we have --edit.
        # This implies a single asset, starting with a (possibly empty) template.
        specs = [{}]

    assets = []
    for spec in specs:
        # 1. start from template
        template_name = spec.get('template', None) or template
        asset = inventory.get_asset_from_template(template_name)
        # 2. fill in asset specification
        asset.update(spec)

        if edit:
            asset = edit_asset(asset, editor)

        # 3. generate asset name (raises on missing required fields)
        name = inventory.generate_asset_name(asset)

        # arguably: faux serials after editing as well, so one can give 'faux' via edit!

        # 4. generate 'path' and pop 'directory' key
        # TODO: Double-check! Is directory guaranteed at this point? No,but we could from path
        #       Also: do we have a default for `path`? Yes.

        dir = path if path else inventory.repo.git.root / asset.get('directory', '')
        asset['path'] = dir / name
        asset.pop('directory', None)
        assets.append(asset)

    # TODO: Editing too late. Verification for name, etc. needs to come afterwards!
    #       But: Interactively editing a bunch, implies you want to know and correct something invalidate right away
    #       before proceeding to the next one. Hence, editor validation needs to include name generation path
    #       availability, etc.

    # verify that the asset paths are unique/available
    inventory.asset_paths_available(assets)

    for asset in assets:
        # TODO: validate assets before offering to commit. This has to be done after
        # they are build, their values are set, and they were opened to edit
        # Note: Availability was checked. If edited, YAML check was passed. Uniqueness?

        inventory.add_asset(asset)

    if inventory.operations_pending():
        ui.print("The following will be created:")
        for line in inventory.diff():
            ui.print(line)
        if ui.request_user_response("Create assets? (y/n) "):
            if not message:
                operation_paths = [
                    op.operands[0].get("path")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['new_assets']]
                message = inventory.repo.generate_commit_message(
                    cmd="new",
                    modified=operation_paths)
            inventory.commit(message=message)
            return
    ui.print('No new assets created.')


def onyo_rm(inventory: Inventory,
            path: Iterable[Path] | Path,
            message: Optional[str]) -> None:
    """Delete assets and/or directories from the inventory.

    Parameters
    ----------
    inventory: Inventory
        The inventory in which assets and/or directories will be deleted.

    path: Path or Iterable of Path
        List of paths to assets and/or directories to delete from the Inventory.
        If any path given is not valid, none of them gets deleted.

    message: str, optional
        An optional string to overwrite Onyo's default commit message.
    """
    paths = [path] if not isinstance(path, (list, set, tuple)) else path

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
                operation_paths = [
                    op.operands[0]
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['remove_assets'] or
                    op.operator == OPERATIONS_MAPPING['remove_directories']]
                message = inventory.repo.generate_commit_message(
                    cmd="rm",
                    modified=operation_paths)
            inventory.commit(message)
            return
    ui.print('Nothing was deleted.')


def onyo_set(inventory: Inventory,
             paths: Optional[Iterable[Path]],
             keys: Dict[str, str | int | float],
             filter_strings: list[str],
             rename: bool,
             depth: int,
             message: Optional[str] = None) -> Optional[str]:
    """Set key-value pairs of assets, and change asset names.

    Parameters
    ----------
    inventory: Inventory
        The Inventory in which to set key/values for assets.

    paths: Path or Iterable of Path, optional
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

    filter_strings: list of str
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
    if not paths:
        paths = [Path.cwd()]

    if not rename and any(k in inventory.repo.get_required_asset_keys() for k in keys.keys()):
        raise ValueError("Can't change required keys without --rename.")
    # TODO: `keys` must not contain RESERVED_KEYS

    non_inventory_paths = [str(p) for p in paths if not inventory.repo.is_asset_path(p) and not inventory.repo.is_inventory_dir(p)]
    if non_inventory_paths:
        raise ValueError("The following paths are neither an inventory directory nor an asset:\n%s",
                         "\n".join(non_inventory_paths))
    filters = set_filters(filter_strings, repo=inventory.repo) if filter_strings else None
    # TODO: We are only interested in paths here. Factor that in for changing get_asset_by_query, when
    #       rewriting `onyo get`.
    asset_paths_to_set = [p for p, _ in get_assets_by_query(
        inventory.repo.asset_paths, keys=None, paths=paths, depth=depth, filters=filters)]

    for path in asset_paths_to_set:
        asset = inventory.get_asset(path)
        new_content = asset.copy()
        new_content.update(keys)
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
                operation_paths = [
                    op.operands[0].get("path")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['modify_assets']]
                message = inventory.repo.generate_commit_message(
                    cmd="set",
                    keys=[str(k) for k in keys.keys()],
                    modified=operation_paths)
            inventory.commit(message=message)
            return
    ui.print("No assets updated.")


def onyo_tree(repo: OnyoRepo,
              paths: list[Path]) -> None:
    """Print the directory tree of paths.

    Parameters
    ----------
    repo: OnyoRepo
        The Onyo Repository in which the directories to display are located.

    paths: list of Path
        The paths to directories for which to print the directory tree.
        If no path is specified, prints the directory tree for CWD.

    Raises
    ------
    ValueError
        If paths are invalid.
    """
    # sanitize the paths
    non_inventory_dirs = [str(p) for p in paths if not repo.is_inventory_dir(p)]
    if non_inventory_dirs:
        raise ValueError("The following paths are not inventory directories: %s" %
                         '\n'.join(non_inventory_dirs))

    # run it
    ret = subprocess.run(
        ['tree', *map(str, paths)], capture_output=True, text=True, check=True)
    # print tree output
    ui.print(ret.stdout)


def unset(repo: OnyoRepo,
          paths: Optional[Iterable[Path]],
          keys: list[str],
          filter_strings: list[str],
          depth: Optional[int],
          message: Optional[str]) -> None:
    """Remove keys from assets.
    TODO: Needs complete re-factoring, thereby the doc-string is incomplete.

    Parameters
    ----------
    repo: OnyoRepo
        TODO

    paths: Path or Iterable of Path, optional
        TODO

    keys: list of str
        TODO

    filter_strings: list of str
        TODO

    depth: int, optional
        TODO

    message: str, optional
        An optional string to overwrite Onyo's default commit message.

    Raises
    ------
    ValueError
        TODO
    """
    from onyo.lib.command_utils import unset as ut_unset
    from .assets import write_asset_file

    if not paths:
        paths = [Path.cwd()]

    non_inventory_paths = [str(p) for p in paths if not repo.is_asset_path(p) and not repo.is_inventory_dir(p)]
    if non_inventory_paths:
        raise ValueError("The following paths are neither an inventory directory nor an asset:\n%s",
                         "\n".join(non_inventory_paths))

    filters = set_filters(filter_strings, repo=repo) if filter_strings else None
    paths = get_assets_by_query(
        repo.asset_paths, keys=None, paths=paths, depth=depth, filters=filters)
    paths = [a[0] for a in paths]

    modifications = ut_unset(repo, paths, keys, depth)

    diffs = [m[2] for m in modifications if m[2] != []]
    # display changes
    if diffs:
        ui.print("The following assets will be changed:")
        if diffs:
            for d in diffs:
                for line in d:
                    ui.print(line)
    else:
        ui.print("No assets containing the specified key(s) could be found. No assets updated.")
        return

    if diffs:
        if ui.request_user_response("Update assets? (y/n) "):
            to_commit = []
            for m in modifications:
                write_asset_file(m[0], m[1])
                to_commit.append(m[0])
                if not message:
                    paths = [p for p in to_commit]
                    # TODO: change after refactoring to:
                    # operation_paths = [
                    #    op.operands[0].get("path")
                    #    for op in inventory.operations
                    #    if op.operator == OPERATIONS_MAPPING['modify_assets']]
                    message = repo.generate_commit_message(
                        cmd="unset",
                        keys=keys,
                        modified=paths)
                repo.git.stage_and_commit(paths=to_commit,
                                          message=message)
            return
    ui.print("No assets updated.")
