from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import (
    ParamSpec,
    TYPE_CHECKING,
    TypeVar,
)
from functools import wraps

from rich import box
from rich.table import Table  # pyre-ignore[21] for some reason pyre doesn't find Table

from onyo.lib.command_utils import (
    inline_path_diff,
    natural_sort,
    print_diff,
)
from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    ASSET_DIR_FILE_NAME,
    ONYO_CONFIG,
    RESERVED_KEYS,
    SORT_ASCENDING,
    SORT_DESCENDING,
)
from onyo.lib.exceptions import (
    InvalidArgumentError,
    InventoryDirNotEmpty,
    NotADirError,
    NoopError,
    OnyoInvalidRepoError,
    OnyoRepoError,
    PendingInventoryOperationError,
)
from onyo.lib.items import (
    Item,
    ItemSpec,
)
from onyo.lib.inventory import Inventory, OPERATIONS_MAPPING
from onyo.lib.onyo import OnyoRepo
from onyo.lib.pseudokeys import PSEUDO_KEYS
from onyo.lib.ui import ui
from onyo.lib.utils import (
    deduplicate,
    write_asset_to_file,
)

if TYPE_CHECKING:
    from collections import UserDict
    from typing import (
        Callable,
        Dict,
        Generator,
        Iterable,
        Literal,
    )
    from onyo.lib.consts import sort_t

log: logging.Logger = logging.getLogger('onyo.commands')

T = TypeVar('T')
P = ParamSpec('P')


def raise_on_inventory_state(func: Callable[P, T]) -> Callable[P, T]:
    r"""Raise if the ``Inventory`` state is unsafe to run an onyo command.

    Decorator for Onyo commands. Requires an ``Inventory`` to be among the
    arguments of the decorated function.

    Assesses whether the worktree is clean and there are no pending operations
    in an ``Inventory``.
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
    r"""Run integrity checks on an Onyo repository and its contents.

    The following tests are available:

    * ``anchors``: directories (outside of ``.onyo/``) have an ``.anchor`` file
    * ``asset-yaml``: asset YAML is valid
    * ``clean-tree``: git reports no changed (staged or unstaged) or untracked files

    Like Git, Onyo ignores files specified in ``.gitignore``.

    Parameters
    ----------
    repo
        The repository on which to perform the fsck.
    tests
        A list of tests to run. By default, all tests are run.

    Raises
    ------
    ValueError
        A specified test does not exist.
    OnyoInvalidRepoError
        One or more tests failed.
    """

    from functools import partial
    from onyo.lib.utils import validate_yaml

    all_tests = {
        # TODO: fsck would probably want to relay or analyze `git-status` output, rather
        # than just get a bool for clean worktree:
        "anchors": repo.validate_anchors,
        "asset-yaml": partial(validate_yaml, {repo.git.root / a for a in repo.asset_paths}),
        "clean-tree": repo.git.is_clean_worktree,
    }
    if tests:
        # only known tests are accepted
        if [x for x in tests if x not in all_tests.keys()]:
            raise ValueError("Invalid test requested. Available tests are: {}".format(', '.join(all_tests.keys())))
    else:
        tests = list(all_tests.keys())

    # run the selected tests
    for key in tests:
        ui.log(f"'{key}' starting")

        if not all_tests[key]():
            ui.log_debug(f"'{key}' failed")
            raise OnyoInvalidRepoError(f"'{repo.git.root}' failed fsck test '{key}'")

        ui.log(f"'{key}' succeeded")


@raise_on_inventory_state
def onyo_config(inventory: Inventory,
                config_args: list[str]) -> None:
    r"""Set, query, and unset Onyo repository configuration options.

    Arguments are passed through directly to ``git config``. Those that change
    the config file location (such as ``--system``) are not allowed.

    Parameters
    ----------
    inventory
        The Inventory to configure.
    config_args
        Options and arguments to pass to the underlying call of ``git config``.
    """

    from onyo.lib.command_utils import allowed_config_args

    allowed_config_args(config_args)
    # repo version shim
    try:
        v2_cfg = config_args.index("onyo.assets.name-format")
    except ValueError:
        # not found is fine
        v2_cfg = None
    if v2_cfg is not None and inventory.repo.version == '1':
        config_args = config_args[:v2_cfg] + ['onyo.assets.filename'] + config_args[v2_cfg + 1:]
    # end repo version shim
    subprocess.run(["git", 'config', '-f', str(ONYO_CONFIG)] +
                   config_args, cwd=inventory.repo.git.root, check=True)

    if not any(a.startswith('--get') or a == '--list' for a in config_args):
        # commit if there are any changes
        try:
            inventory.repo.commit(ONYO_CONFIG,
                                  'config: modify repository config')
        except subprocess.CalledProcessError as e:
            if "no changes added to commit" in e.stdout or "nothing to commit" in e.stdout:
                ui.print("No changes to commit.")
                return
            raise


def _edit_asset(inventory: Inventory,
                asset: Item,
                operation: Callable,
                editor: str | None) -> Item:
    r"""Edit an ``asset`` (as a temporary file) with ``editor``.

    A helper for ``onyo_edit()`` and ``onyo_new(edit=True)``.

    The asset content is edited as a temporary file. Once the editor is done,
    the ``operation`` function is executed to validate the content.

    The user is then presented with a diff and prompted on how to proceed
    (accept, edit, skip, or abort).

    If accepted, the changes are applied to the original asset and the temporary
    file is deleted.

    Parameters
    ----------
    inventory
        The Inventory containing the asset to edit.
    asset
        The asset to edit.
    operation
        Function to validate the edited asset, which shall raise if the asset
        isn't valid for that purpose.
        e.g. :py:meth:`onyo.lib.inventory.Inventory.modify_asset`
    editor
        The shell string to execute as the editor. The path to a temporary file
        is appended to the string.
        By default uses the result of ``OnyoRepo.get_editor()``.
    """

    from shlex import quote
    from onyo.lib.consts import RESERVED_KEYS
    from onyo.lib.utils import get_temp_file, get_asset_content

    if not editor:
        editor = inventory.repo.get_editor()

    # preserve the original pseudo-keys to re-assign them later
    reserved_keys = {k: v for k, v in asset.items() if k in list(PSEUDO_KEYS.keys()) + ['template'] and v is not None}
    disallowed_keys = RESERVED_KEYS + list(PSEUDO_KEYS.keys())
    disallowed_keys.remove('onyo.is.directory')
    disallowed_keys.remove('onyo.path.parent')

    tmp_path = get_temp_file()
    write_asset_to_file(asset, path=tmp_path)

    # store operations queue length in case we need to roll-back
    queue_length = len(inventory.operations)
    # kick off editing process
    while True:
        # execute the editor
        subprocess.run(f'{editor} {quote(str(tmp_path))}', check=True, shell=True)
        operations = None
        try:
            tmp_asset = ItemSpec(get_asset_content(tmp_path))
            if 'onyo.is.directory' in tmp_asset.keys():
                # 'onyo.is.directory' currently is the only modifiable, reserved key
                reserved_keys['onyo.is.directory'] = tmp_asset['onyo.is.directory']

            # Check disallowed keys before we make an `Item` of this, because
            # that will have all pseudo-keys.
            if any(k in disallowed_keys for k in tmp_asset.keys()):
                raise ValueError(f"Can't set any of the keys ({', '.join(disallowed_keys)}).")
            asset = Item()
            # keep exact objects for ruamel-based roundtrip:
            asset.data = tmp_asset.data
            # ^ This kills pseudo-keys. Re-add those, that aren't specified
            asset.update({k: v for k, v in PSEUDO_KEYS.items() if k not in tmp_asset})
            asset.update(reserved_keys)

            operations = operation(asset)
        except NoopError:
            pass
        except Exception as e:
            # TODO: dedicated type: OnyoValidationError?
            # remove possibly added operations from the queue:
            if queue_length < len(inventory.operations):
                inventory.operations = inventory.operations[:queue_length]
            ui.error(e)

            response = ui.request_user_response(
                "Continue (e)diting asset, (s)kip asset or (a)bort command)? ",
                default='a',  # non-interactive has to fail
                answers=[('edit', ['e', 'E', 'edit']),
                         ('skip', ['s', 'S', 'skip']),
                         ('abort', ['a', 'A', 'abort'])
                         ]
            )
            match response:
                case 'edit':
                    continue
                case 'skip':
                    tmp_path.unlink()
                    return Item()
                case 'abort':
                    # Error message was already passed to ui. Raise a different exception instead.
                    # TODO: Own exception class for that purpose? Can we have no message at all?
                    #       -> Make possible in main.py
                    tmp_path.unlink()
                    raise ValueError("Command canceled.") from e
                case _:
                    # should not be possible
                    raise RuntimeError(f"Unexpected response: {response}")

        # if no edits were made, move on
        if not operations:
            break

        # show diff and ask for confirmation
        ui.print("Effective changes:")
        for op in operations:
            print_diff(op)

        response = ui.request_user_response(
            "Accept changes? (y)es / continue (e)diting / (s)kip asset / (a)bort command ",
            default='yes',
            answers=[('accept', ['y', 'Y', 'yes']),
                     ('edit', ['e', 'E', 'edit']),
                     ('skip', ['s', 'S', 'skip']),
                     ('abort', ['a', 'A', 'abort'])
                     ]
        )
        if response == 'accept':
            break
        else:
            # remove possibly added operations from the queue:
            if queue_length < len(inventory.operations):
                inventory.operations = inventory.operations[:queue_length]

        match response:
            case 'edit':
                continue
            case 'skip':
                tmp_path.unlink()
                return Item()
            case 'abort':
                tmp_path.unlink()
                raise KeyboardInterrupt
            case _:
                # should not be possible
                raise RuntimeError(f"Unexpected response: {response}")

    tmp_path.unlink()
    return asset


@raise_on_inventory_state
def onyo_edit(inventory: Inventory,
              paths: list[Path],
              message: str | None,
              auto_message: bool | None = None) -> None:
    r"""Edit the content of assets.

    Parameters
    ----------
    inventory
        The Inventory containing the assets to edit.
    paths
        Paths of assets to edit.
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    ValueError
        ``paths`` is empty or contains a path to a non-asset.
    """

    from functools import partial

    if auto_message is None:
        auto_message = inventory.repo.auto_message
    if not paths:
        raise ValueError("At least one asset must be specified.")

    non_asset_paths = [str(p) for p in paths if not inventory.repo.is_asset_path(p)]
    if non_asset_paths:
        raise ValueError("The following paths are not assets:\n%s" %
                         "\n".join(non_asset_paths))

    editor = inventory.repo.get_editor()
    for path in paths:
        asset = inventory.get_item(path)
        _edit_asset(inventory, asset, partial(inventory.modify_asset, asset), editor)

    if inventory.operations_pending():
        ui.print('\n' + inventory.operations_summary())

        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].get("onyo.path.relative")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['modify_assets']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="edit [{len}]: {operation_paths}",
                    len=len(operation_paths),
                    operation_paths=operation_paths) + (message or "")
            inventory.commit(message=message)
            return

    ui.print('No assets updated.')


@raise_on_inventory_state
def onyo_get(inventory: Inventory,
             include: list[Path] | None = None,
             exclude: list[Path] | Path | None = None,
             depth: int = 0,
             machine_readable: bool = False,
             match: list[Callable[[dict], bool]] | list[list[Callable[[dict], bool]]] | None = None,
             keys: list[str] | None = None,
             sort: dict[str, sort_t] | None = None,
             types: list[Literal['assets', 'directories']] | None = None,
             ) -> list[dict]:
    r"""Query the key-values of inventory items.

    All keys, both on-disk YAML and :py:data:`onyo.lib.pseudokeys.PSEUDO-KEYS`,
    can be queried, matched, and sorted. Dictionary subkeys are addressed
    using a period (e.g. ``model.name``).

    Parameters
    ----------
    inventory
        The Inventory to query.
    include
        Paths under which to query. Default is inventory root.

        Passed to :py:func:`onyo.lib.inventory.Inventory.get_items`.
    exclude
        Paths to exclude (i.e. results underneath will not be returned).

        Passed to :py:func:`onyo.lib.inventory.Inventory.get_items`.
    depth
        Number of levels to descend into the directories specified by
        ``include``. A depth of ``0`` descends recursively without limit.

        Passed to :py:func:`onyo.lib.inventory.Inventory.get_items`.
    machine_readable
        Print results in a machine-friendly format (no headers; separate values
        with a single tab) rather than a human-friendly output (headers and
        padded whitespace to align columns).
    match
        Callables suited for use with builtin :py:func:`filter`. They
        are passed an :py:class:`onyo.lib.items.Item` and are expected to
        return a ``bool``. All keys can be matched, and are not limited to
        those specified by ``keys``.

        Within a list of Callables, all must return True for an Item to
        match. When multiple lists are passed, only one list of Callables
        must match for an Item to match (e.g. each list of Callables is
        connected with a logical ``or``).

        Passed to :py:func:`onyo.lib.inventory.Inventory.get_items`.
    keys
        Keys to print the values of. Default is asset-name keys and ``path``.
    sort
        Dictionary of keys to sort the resulting items. The value specifies
        which type of sort to use (:py:data:`onyo.lib.consts.SORT_ASCENDING`
        and :py:data:`onyo.lib.consts.SORT_DESCENDING`). They are applied in
        the order they are defined in the dictionary. All keys can be sorted,
        and are not limited to those specified by ``keys``.
        Default is ``{'onyo.path.relative': SORT_ASCENDING}``
    types
        Types of inventory items to consider. Equivalent to
        ``onyo.is.asset=True`` and ``onyo.is.directory=True``.
        Default is ``['assets']``.

        Passed to :py:func:`onyo.lib.inventory.Inventory.get_items`.

    Raises
    ------
    ValueError
        Invalid argument
    """

    from onyo.lib.consts import TAG_MAP_OUTPUT, TAG_UNSET

    selected_keys = keys.copy() if keys else None
    include = include or [inventory.root]

    # validate path arguments
    invalid_paths = set(p
                        for p in include  # pyre-ignore[16]  `include` not Optional anymore here
                        if not p.exists() or not inventory.repo.is_item_path(p.resolve()))
    if invalid_paths:
        err_str = '\n'.join([str(x) for x in invalid_paths])
        raise ValueError(f"The following paths are not part of the inventory:\n{err_str}")

    allowed_sorting = [SORT_ASCENDING, SORT_DESCENDING]
    if sort and not all(v in allowed_sorting for k, v in sort.items()):
        raise ValueError(f"Allowed sorting modes: {', '.join(allowed_sorting)}")

    selected_keys = selected_keys or inventory.repo.get_asset_name_keys() + ['onyo.path.relative']
    results = list(inventory.get_items(include=include,
                                       exclude=exclude,
                                       depth=depth,
                                       match=match,  # pyre-ignore[6]
                                       types=types))

    # sort results before filtering/replacing, so all keys can be sorted
    results = natural_sort(
        items=results,
        keys=sort or {'onyo.path.relative': SORT_ASCENDING})  # pyre-ignore[6]

    # reduce results to just the `selected_keys`
    results = [{k: r[k] if k in r else TAG_UNSET
                for k in selected_keys}
               for r in results]

    # replace structures with an indication of type.
    for symbol in TAG_MAP_OUTPUT:
        results = [{k: symbol if isinstance(v, TAG_MAP_OUTPUT[symbol]) else v
                    for k, v in r.items()}
                   for r in results]

    if machine_readable:
        sep = '\t'
        for data in results:
            values = sep.join([str(data[k]) for k in selected_keys])
            ui.print(f'{values}')
    else:
        if results:
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
            ui.rich_print('No inventory items matching the filter(s) were found')

    return results


@raise_on_inventory_state
def onyo_history(inventory: Inventory,
                 path: Path,
                 interactive: bool | None = None) -> None:
    r"""Display the history of a path.

    Only one ``path`` is accepted due to ``git log --follow``'s limitation.

    Parameters
    ----------
    inventory
        The Inventory to display the history of.
    path
        Path to display the history of.
    interactive
        Force interactive mode on/off.
        ``None`` autodetects if the TTY is interactive.

    Raises
    ------
    ValueError
        The configuration key is not set or the configured history program
        cannot be found by ``which``.
    """

    from shlex import quote

    history_cmd = _get_history_cmd(inventory, interactive)
    # do not catch exceptions; let them bubble up with their exit codes
    subprocess.run(f'{history_cmd} {quote(str(path))}', check=True, shell=True)


def _get_history_cmd(inventory: Inventory,
                     interactive: bool | None = None) -> str:
    r"""Get the command to display history.

    The command is selected according to the (non)interactive mode and
    verified that it exists.

    A helper for ``onyo_history()``.

    Parameters
    ----------
    inventory
        The Inventory from which to get the configured history program.
    interactive
        Force interactive mode on/off.
        ``None`` autodetects if the TTY is interactive.

    Raises
    ------
    ValueError
        The configuration key is either not set or the configured history
        program cannot be found by ``which``.
    """

    from shutil import which
    from sys import stdout

    match interactive:
        case True:
            config_name = 'onyo.history.interactive'
        case False:
            config_name = 'onyo.history.non-interactive'
        case _:
            config_name = 'onyo.history.interactive' if stdout.isatty() else 'onyo.history.non-interactive'

    history_cmd = inventory.repo.get_config(config_name)
    if not history_cmd:
        raise ValueError(f"'{config_name}' is unset and is required to display history.\n"
                         f"Please see 'onyo config --help' for information about how to set it.")

    history_executable = history_cmd.split()[0]
    if not which(history_executable):
        raise ValueError(f"'{history_cmd}' acquired from '{config_name}'. "
                         f"The program '{history_executable}' was not found. Exiting.")

    return history_cmd


@raise_on_inventory_state
def onyo_mkdir(inventory: Inventory,
               dirs: list[Path],
               message: str | None = None,
               auto_message: bool | None = None) -> None:
    r"""Create directories or convert Asset Files into Asset Directories.

    Intermediate directories are created as needed (i.e. parent and child
    directories can be created in one call).

    An empty `.anchor` file is added to each directory, to ensure that git
    tracks them even when empty.

    If ``dirs`` contains a path that is already a directory or a protected path,
    then no new directories are created and an error is raised.

    At least one path is required.

    Parameters
    ----------
    inventory
        The Inventory in which to create directories or convert asset files.
    dirs
        Paths of directories to create.
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    NoopError
        ``dirs`` is empty.
    """

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    if not dirs:
        raise NoopError("At least one directory path must be specified.")

    for d in deduplicate(dirs):  # pyre-ignore[16]
        inventory.add_directory(Item(d, repo=inventory.repo))

    if inventory.operations_pending():
        ui.print(inventory.operations_summary())

        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['new_directories']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="mkdir [{len}]: {operation_paths}\n",
                    len=len(operation_paths),
                    operation_paths=sorted(operation_paths)) + (message or "")

            inventory.commit(message=message)
            return

    ui.print('No directories created.')


def _move_asset_or_dir(inventory: Inventory,
                       source: Item,
                       destination: Item) -> None:
    r"""Move a source asset or directory into a destination directory.

    Parameters
    ----------
    inventory
        The Inventory to operate on.
    source
        Asset or directory to move.
    destination
        Directory to move the source into.
    """

    if source['onyo.is.asset']:
        inventory.move_asset(source, destination)
        return
    inventory.move_directory(source, destination)


def _maybe_rename(inventory: Inventory,
                  src: Path,
                  dst: Path) -> None:
    r"""Rename a directory. Catch and clean if it's an Asset Directory."""

    try:
        inventory.rename_directory(inventory.get_item(src), dst)
    except NotADirError as e:
        # We tried to rename an asset dir.
        inventory.reset()
        raise ValueError("Renaming an asset requires the 'set' command.") from e


@raise_on_inventory_state
def onyo_mv(inventory: Inventory,
            source: list[Path] | Path,
            destination: Path,
            message: str | None = None,
            auto_message: bool | None = None) -> None:
    r"""Move assets and/or directories, or rename a directory.

    If the ``destination`` is an asset file, it is converted into an Asset
    Directory first, and then the ``source``\ (s) moved into it.

    If a single source directory is given and the ``destination`` is a
    non-existing directory, the source will be renamed.

    Parameters
    ----------
    inventory
        The Inventory in which to move assets and/or directories.
    source
        A list of source paths to move to ``destination``.
    destination
        The path to which ``source``\ (s) will be moved (or the new name, if a
        single source directory).
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    ValueError
        If multiple source paths are specified to be renamed.
    """

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    sources = [source] if not isinstance(source, list) else source
    implicit_move = False

    if destination.exists():
        # Move Mode
        subject_prefix = "mv"
        implicit_move = True
        # destination Asset File needs to be converted into Asset Directory first
        dst_item = inventory.get_item(destination)
        if dst_item['onyo.is.asset'] and not dst_item['onyo.is.directory']:
            inventory.add_directory(dst_item)

        for s in sources:
            _move_asset_or_dir(inventory, inventory.get_item(s), dst_item)
    elif len(sources) == 1 and sources[0].name == destination.name:
        # Move Mode: explicit destination name
        # The destination does not exist, but is named the same as the source.
        # e.g. mv example dir/example
        subject_prefix = "mv"
        _move_asset_or_dir(inventory, inventory.get_item(sources[0]), inventory.get_item(destination.parent))
    elif len(sources) == 1 and sources[0].is_dir() and destination.parent.is_dir():
        if sources[0].parent == destination.parent:
            # Rename Mode
            # e.g. mv example different
            subject_prefix = "ren"
            _maybe_rename(inventory, sources[0], destination)
        else:
            # Move + Rename Mode: different parents (rename) and different source/dest names
            # e.g. mv example dir/different
            subject_prefix = "mv + ren"
            inventory.move_directory(inventory.get_item(sources[0]), inventory.get_item(destination.parent))
            _maybe_rename(inventory, destination.parent / sources[0].name, destination)
            # TODO: Replace - see issue #546:
            inventory._ignore_for_commit.append(destination.parent / sources[0].name)
    else:
        raise ValueError("Can only move into an existing directory/asset, or rename a single directory.")

    if inventory.operations_pending():
        ui.print(inventory.operations_summary())

        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].relative_to(inventory.root)
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['rename_assets'] or
                    op.operator == OPERATIONS_MAPPING['move_assets'] or
                    op.operator == OPERATIONS_MAPPING['move_directories'] or
                    op.operator == OPERATIONS_MAPPING['rename_directories']]))
                # renames and single item moves use an inline diff for the subject line
                if len(sources) == 1:
                    # NOTE: It would be preferable to extract this information
                    # from inventory.operations (e.g. inventory.operations[0].operator.recorder()),
                    # but recorders are currently inconvenient to use (they even
                    # have a TODO to simplify them to use Inventory).
                    # Furthermore, _record_move() explicitly notes that it
                    # assumes that it's passed the complete paths, which is the
                    # exact same problem that we have here, so it actually
                    # doesn't help us. :-/
                    if implicit_move:
                        # the destination is not explicitly specified
                        # (aka: e.g. onyo mv file dest/)
                        dest = Path(destination / sources[0].name).relative_to(inventory.root)
                    else:
                        dest = destination.relative_to(inventory.root)

                    inline_diff = inline_path_diff(operation_paths[0], dest)
                    ln = len(operation_paths)
                    message = f"{subject_prefix} [{ln}]: {inline_diff}\n" + (message or "")
                else:  # multi-source moves
                    message = inventory.repo.generate_commit_subject(
                        format_string="{prefix} [{ln}]: {operation_paths} -> {destination}\n",
                        prefix=subject_prefix,
                        ln=len(operation_paths),
                        operation_paths=operation_paths,
                        destination=destination.relative_to(inventory.root)) + (message or "")
            inventory.commit(message=message)
            return

    ui.print('Nothing was moved.')


@raise_on_inventory_state
def onyo_new(inventory: Inventory,
             directory: Path | None = None,
             template: Path | str | None = None,
             clone: Path | None = None,
             keys: list[Dict | UserDict] | None = None,
             edit: bool = False,
             message: str | None = None,
             auto_message: bool | None = None) -> None:
    r"""Create new assets and add them to the inventory.

    Destination directories are created if they are missing.

    Asset contents are populated in a waterfall pattern and can overwrite values
    from previous steps:

    1) ``clone`` or ``template``
    2) ``keys``
    3) ``edit`` (i.e. manual user input)

    The keys that comprise the asset filename are required (configured by
    ``onyo.assets.name-format``).

    Parameters
    ----------
    inventory
        The Inventory in which to create new assets.
    directory
        The directory to create new asset(s) in. This cannot be used with the
        ``directory`` Reserved Key.

        If `None` and the ``directory`` Reserved Key is not found, it defaults
        to CWD.
    template
        Path to a template to populate the contents of new assets.

        Relative paths are resolved relative to ``.onyo/templates``.
    clone
        Path of an asset to clone. Cannot be used with the ``template`` argument
        nor the ``template`` Reserved Key.
    keys
        List of dictionaries with key/value pairs to set in the new assets.

        Each key can be defined either ``1`` or ``N`` times (where ``N`` is the number
        of assets to be created). A key that is declared once will apply to all
        new assets, otherwise each will be applied to each new asset in the
        order they were declared.

        Dictionary subkeys can be addressed using a period (e.g. ``model.name``,
        ``model.year``, etc.)
    edit
        Open newly created assets in an editor before they are saved.
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    ValueError
        If information is invalid, missing, or contradictory.
    """

    from copy import deepcopy

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    keys = keys or []
    if not any([keys, edit, template, clone]):
        raise ValueError("Key-value pairs or a template/clone-target must be given.")
    if template and clone:
        raise ValueError("'template' and 'clone' options are mutually exclusive.")

    # get editor early in case it fails
    editor = inventory.repo.get_editor() if edit else ""

    # Note that `keys` can be empty.
    specs = deepcopy(keys)

    # TODO: These validations could probably be more efficient and neat.
    #       For ex., only first dict is actually relevant. It came from --key,
    #       where everything after the first one comes from repetition (However, what about python interface where one
    #       could pass an arbitrary list of dicts? -> requires consistency check
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

    # Generate actual assets:
    if edit and not specs:
        # Special case: No asset specification defined via `keys`, but we have `edit`.
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
            asset = inventory.get_item(clone)
        else:
            t = spec.pop('template', None) or template
            asset = inventory.get_asset_from_template(Path(t) if t else None)
        # 3. fill in asset specification
        asset.update(spec)
        # 4. (try to) add to inventory
        if edit:
            _edit_asset(inventory, asset, inventory.add_asset, editor)
        else:
            inventory.add_asset(asset)

    if inventory.operations_pending():
        if not edit:
            # If `edit` was given, per-asset diffs were already approved. Don't ask again.
            print_diff(inventory)
        ui.print('\n' + inventory.operations_summary())

        if edit or ui.request_user_response("Create assets? (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].get("onyo.path.relative")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['new_assets']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="new [{len}]: {operation_paths}\n",
                    len=len(operation_paths),
                    operation_paths=operation_paths) + (message or "")
            inventory.commit(message=message)
            return

    ui.print('No new assets created.')


@raise_on_inventory_state
def onyo_rm(inventory: Inventory,
            paths: list[Path] | Path,
            message: str | None = None,
            recursive: bool = False,
            auto_message: bool | None = None) -> None:
    r"""Delete assets and/or directories from an inventory.

    Parameters
    ----------
    inventory
        The Inventory in which assets and/or directories will be deleted.
    paths
        Path or List of Paths of assets and/or directories to delete from the
        inventory. If any path is invalid or encounters a problem, none are deleted.
    recursive
        Remove directories recursively.
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.
    """

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    paths = [paths] if not isinstance(paths, list) else paths
    for p in paths:
        item = inventory.get_item(p)
        if p.name in [ANCHOR_FILE_NAME, ASSET_DIR_FILE_NAME]:
            raise InvalidArgumentError(f"Cannot remove onyo-managed files ({p}).\n"
                                       f"You may want to remove {p.parent} instead.")
        if (not item['onyo.is.asset'] and not item['onyo.is.directory']) or \
                item['onyo.is.template']:
            raise InvalidArgumentError(f"{p} is neither an asset nor an inventory directory.\n"
                                       f"You may want to remove this by other means than onyo.")

        if item['onyo.is.asset']:
            inventory.remove_asset(item)
        if item['onyo.is.directory']:
            try:
                inventory.remove_directory(item, recursive=recursive)
            except InventoryDirNotEmpty as e:
                # Enhance message from failed operation with command specific context:
                raise InventoryDirNotEmpty(f"{str(e)}\nDid you forget '--recursive'?") from e

    if inventory.operations_pending():
        ui.print(inventory.operations_summary())

        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0]['onyo.path.relative']
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['remove_assets'] or
                    op.operator == OPERATIONS_MAPPING['remove_directories']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="rm [{len}]: {operation_paths}\n",
                    len=len(operation_paths),
                    operation_paths=operation_paths) + (message or "")
            inventory.commit(message)
            return

    ui.print('Nothing was deleted.')


@raise_on_inventory_state
def onyo_rmdir(inventory: Inventory,
               dirs: list[Path] | Path,
               message: str | None = None,
               auto_message: bool | None = None) -> None:
    r"""Delete empty directories or convert empty Asset Directories into Asset Files.

    If the directory does not exist, the path is protected, or the asset is
    already an Asset File, then an error is raised nothing is modified.

    Parameters
    ----------
    inventory
        The Inventory in which to delete directories or convert asset directories.
    dirs
        Paths of directories to delete or convert.
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    NoopError
        ``dirs`` is empty.
    """

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    if not dirs:
        raise NoopError("At least one directory path must be specified.")

    dirs = [dirs] if not isinstance(dirs, list) else dirs
    for d in deduplicate(dirs):  # pyre-ignore[16]
        try:
            inventory.remove_directory(inventory.get_item(d), recursive=False)
        except InventoryDirNotEmpty as e:
            raise InventoryDirNotEmpty(f"{str(e)}\nCannot remove a non-empty directory.") from e

    if inventory.operations_pending():
        ui.print(inventory.operations_summary())

        if ui.request_user_response("Save changes? No discards all changes. (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].get("onyo.path.relative")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['remove_directories']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="rmdir [{len}]: {operation_paths}\n",
                    len=len(operation_paths),
                    operation_paths=sorted(operation_paths)) + (message or "")

            inventory.commit(message=message)
            return

    ui.print('No directories were removed.')


@raise_on_inventory_state
def onyo_set(inventory: Inventory,
             keys: dict | UserDict,
             assets: list[Path],
             message: str | None = None,
             auto_message: bool | None = None) -> str | None:
    r"""Set key-value pairs in assets.

    Modifying the values of keys used in the asset name will rename the Asset
    File/Directory.

    Parameters
    ----------
    inventory
        The Inventory in which to modify assets.
    assets
        Paths of assets to modify.
    keys
        Key-value pairs to set in assets. Keys that already exist in an asset
        will have their their values overwritten. Keys that do not exist will be
        added and the value set.

        Dictionary subkeys can be addressed using a period (e.g. ``model.name``,
        ``model.year``, etc.)
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    ValueError
        If a given path is invalid or if ``keys`` is empty.
    """

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    if not assets:
        raise ValueError("At least one asset must be specified.")
    if not keys:
        raise ValueError("At least one key-value pair must be specified.")

    disallowed_keys = RESERVED_KEYS + list(PSEUDO_KEYS.keys())
    disallowed_keys.remove("onyo.is.directory")
    if any(k in disallowed_keys for k in keys.keys()):
        raise ValueError(f"Can't set any of the keys ({', '.join(disallowed_keys)}).")

    non_asset_paths = [str(a) for a in assets if not inventory.repo.is_asset_path(a)]
    if non_asset_paths:
        raise ValueError("The following paths aren't assets:\n%s" %
                         "\n".join(non_asset_paths))

    for asset in [inventory.get_item(a) for a in assets]:
        new_content = Item(asset, inventory.repo)
        new_content.update(keys)
        try:
            inventory.modify_asset(asset, new_content)
        except NoopError:
            pass

    if inventory.operations_pending():
        print_diff(inventory)
        ui.print('\n' + inventory.operations_summary())

        if ui.request_user_response("Update assets? (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].get("onyo.path.relative")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING['modify_assets']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="set [{len}] ({keys}): {operation_paths}\n",
                    len=len(operation_paths),
                    keys=list(keys.keys()),
                    operation_paths=operation_paths) + (message or "")
            inventory.commit(message=message)
            return

    ui.print("No assets updated.")


@raise_on_inventory_state
def onyo_tree(inventory: Inventory,
              path: Path,
              description: str | None = None,
              dirs_only: bool = False) -> None:
    r"""Print a directory's child assets and directories in a tree-like format.

    Parameters
    ----------
    inventory
        The Inventory in which the directory is located.
    path
        The directory to build a tree of.
    description
        The string to represent the root node. Usually the verbatim path
        requested by the user (relative, absolute, subdir, etc).
    dirs_only
        Print only directories.

    Raises
    ------
    ValueError
        If ``path`` is not an inventory directory.
    """

    desc = description if description is not None else str(path)

    # sanitize the path
    if not inventory.repo.is_inventory_dir(path):
        raise ValueError(f"The following path is not an inventory directory: {desc}")

    ui.rich_print(f'[bold][sandy_brown]{desc}[/sandy_brown][/bold]')
    for line in _tree(path, dirs_only=dirs_only):
        ui.rich_print(line)


def _tree(dir_path: Path,
          prefix: str = '',
          dirs_only: bool = False) -> Generator[str, None, None]:
    r"""Yield lines that assemble tree-like output, stylized by rich.

    Parameters
    ----------
    dir_path
        Path of directory to yield a tree of.
    prefix
        Prefix lines with this string. In practice, only useful by ``_tree()``
        itself recursing into directories.
    dirs_only
        Yield only directories.
    """
    space = '    '
    pipe =  '│   '  # noqa: E222
    tee =   '├── '  # noqa: E222
    last =  '└── '  # noqa: E222

    # get and sort the children
    children = sorted(list(dir_path.iterdir()))
    for path in children:
        path_is_dir = path.is_dir()  # don't stat the same path multiple times
        if dirs_only and not path_is_dir:
            continue
        # ignore hidden files/dirs
        if path.name[0] == '.':
            continue

        # choose child prefix
        child_prefix = tee  # ├──
        if path == children[-1]:
            child_prefix = last  # └──

        # colorize directories
        path_name = path.name
        if path_is_dir:
            path_name = f'[bold][sandy_brown]{path.name}[/sandy_brown][/bold]'

        yield f'{prefix}{child_prefix}{path_name}'

        # descend into directories
        if path_is_dir:
            next_prefix_level = pipe if child_prefix == tee else space
            yield from _tree(path, prefix=prefix + next_prefix_level, dirs_only=dirs_only)


def onyo_tsv_to_yaml(tsv: Path) -> None:
    r"""Convert a TSV file to YAML.

    Convert a tabular file (e.g. TSV, CSV) to YAML suitable for passing to
    ``onyo new`` and ``onyo set``.

    The header declares the key names to be populated. The values to populate
    documents are declared with one line per YAML document.

    The output is printed to stdout as a multiple document YAML file (each
    document is separated by a ``---`` line).

    Parameters
    ----------
    tsv
        Path to a **TSV** file.

    Raises
    ------
    ValueError
        If information is invalid, missing, or contradictory.
    """

    import csv
    from io import StringIO

    from onyo.lib.utils import get_patched_yaml

    dicts = []
    with tsv.open('r', newline='') as tsv_file:
        reader = csv.DictReader(tsv_file, delimiter='\t')

        # check for headers
        if reader.fieldnames is None:
            raise ValueError(f"No header fields in tsv {str(tsv)}")

        dicts = [ItemSpec(row) for row in reader]

        # check for content
        if not dicts:
            raise ValueError(f"Headers but no content in tsv {str(tsv)}")

        # Check if any lines have more values than columns. These are stored in the `None` key.
        # Note: start at 1 to give the correct line number (header + index of dict)
        for i, d in enumerate(dicts, start=1):
            if None in d.keys() and d[None] != ['']:
                raise ValueError(f"Values exceed number of columns in {str(tsv)} at line {i}: {d[None]}")

    # build YAML stream
    yaml = get_patched_yaml()
    yaml.explicit_start = True
    s = StringIO()
    for d in dicts:
        yaml.dump(d.data, s)

    ui.print(s.getvalue(), end='')


@raise_on_inventory_state
def onyo_unset(inventory: Inventory,
               keys: Iterable[str],
               assets: list[Path],
               message: str | None = None,
               auto_message: bool | None = None) -> None:
    r"""Remove keys from assets.

    Keys that are used in asset names (see the ``onyo.assets.name-format``
    configuration option) cannot be unset.

    Parameters
    ----------
    inventory
        The Inventory in which to modify assets.
    keys
        List of keys to unset in assets.

        Dictionary subkeys can be addressed using a period (e.g. ``model.name``,
        ``model.year``, etc.).
    assets
        Paths of assets to modify.
    message
        Commit message to append to the auto-generated message.
    auto_message
        Generate a commit-message subject line.
        If ``None``, lookup the config value from ``onyo.commit.auto-message``.

    Raises
    ------
    ValueError
        If ``assets`` contains  invalid paths, ``keys`` is empty, or an keys in
        an asset's name are attempted to be unset.
    """

    if auto_message is None:
        auto_message = inventory.repo.auto_message

    if not keys:
        raise ValueError("At least one key must be specified.")
    non_asset_paths = [str(a) for a in assets if not inventory.repo.is_asset_path(a)]
    if non_asset_paths:
        raise ValueError("The following paths aren't assets:\n%s" % "\n".join(non_asset_paths))
    if any(k in inventory.repo.get_asset_name_keys() for k in keys):
        raise ValueError("Can't unset asset name keys.")
    # TODO: Actual Namespaces! Key must not start with `onyo.` What about aliases?
    if any(k in RESERVED_KEYS or k.startswith("onyo.") for k in keys):
        raise ValueError(f"Can't unset reserved keys ({', '.join(RESERVED_KEYS)}) "
                         f"or keys in 'onyo.' namespace (pseudo keys)")

    for asset in [inventory.get_item(a) for a in assets]:
        new_content = Item(asset, inventory.repo)
        for key in keys:
            try:
                new_content.pop(key)
            except KeyError:
                ui.log_debug(f"{key} not in {asset}")

        try:
            inventory.modify_asset(asset, new_content)
        except NoopError:
            pass

    if inventory.operations_pending():
        print_diff(inventory)
        ui.print('\n' + inventory.operations_summary())

        if ui.request_user_response("Update assets? (y/n) "):
            if auto_message:
                operation_paths = sorted(deduplicate([  # pyre-ignore[6]
                    op.operands[0].get("onyo.path.relative")
                    for op in inventory.operations
                    if op.operator == OPERATIONS_MAPPING[
                        'modify_assets']]))
                message = inventory.repo.generate_commit_subject(
                    format_string="unset [{len}] ({keys}): {operation_paths}\n",
                    len=len(operation_paths),
                    keys=keys,
                    operation_paths=operation_paths) + (message or "")
            inventory.commit(message=message)
            return

    ui.print("No assets updated.")
