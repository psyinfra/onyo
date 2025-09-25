from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import (
    Callable,
    TYPE_CHECKING,
)

from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    ASSET_DIR_FILE_NAME,
)
from onyo.lib.differs import (
    differ_modify_asset,
    differ_move_asset,
    differ_move_directory,
    differ_new_asset,
    differ_new_directory,
    differ_remove_asset,
    differ_remove_directory,
    differ_rename_asset,
    differ_rename_directory,
)
from onyo.lib.exceptions import (
    InvalidInventoryOperationError,
    InventoryDirNotEmpty,
    NoopError,
    NotADirError,
    NotAnAssetError,
)
from onyo.lib.executors import (
    exec_modify_asset,
    exec_move_asset,
    exec_move_directory,
    exec_new_asset,
    exec_new_directory,
    exec_remove_asset,
    exec_remove_directory,
    exec_rename_asset,
    exec_rename_directory,
    generic_executor,
)
from onyo.lib.items import (
    Item,
    ItemSpec,
)
from onyo.lib.onyo import OnyoRepo
from onyo.lib.pseudokeys import PSEUDO_KEYS
from onyo.lib.recorders import (
    record_modify_asset,
    record_move_asset,
    record_move_directory,
    record_new_asset,
    record_new_directory,
    record_remove_asset,
    record_remove_directory,
    record_rename_asset,
    record_rename_directory,
)
from onyo.lib.utils import (
    deduplicate,
)
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Generator,
        Iterable,
        Literal,
    )
    from collections import UserDict


@dataclass
class InventoryOperator:
    r"""Representation of a type of Inventory Operation.

    Groups together the Callables to execute, diff, and record an operation.

    See :py:data:`OPERATIONS_MAPPING`.
    """

    executor: Callable
    differ: Callable
    recorder: Callable


@dataclass
class InventoryOperation(object):
    r"""Representation of an individual pending Inventory Operation.

    Groups together the intended :py:class:`InventoryOperator`, its targets, and
    repo.
    """

    operator: InventoryOperator
    operands: tuple
    repo: OnyoRepo

    def diff(self) -> Generator[str, None, None]:
        r"""Generate the anticipated diff of executing the operation."""

        yield from self.operator.differ(repo=self.repo, operands=self.operands)

    def execute(self) -> tuple[list[Path], list[Path]]:
        r"""Execute the Inventory Operation."""

        return self.operator.executor(repo=self.repo, operands=self.operands)


OPERATIONS_MAPPING: dict = {
    'modify_assets': InventoryOperator(
        executor=exec_modify_asset,
        differ=differ_modify_asset,
        recorder=record_modify_asset,
    ),
    'move_assets': InventoryOperator(
        executor=exec_move_asset,
        differ=differ_move_asset,
        recorder=record_move_asset,
    ),
    'move_directories': InventoryOperator(
        executor=exec_move_directory,
        differ=differ_move_directory,
        recorder=record_move_directory,
    ),
    'new_assets': InventoryOperator(
        executor=exec_new_asset,
        differ=differ_new_asset,
        recorder=record_new_asset,
    ),
    'new_directories': InventoryOperator(
        executor=exec_new_directory,
        differ=differ_new_directory,
        recorder=record_new_directory,
    ),
    'remove_assets': InventoryOperator(
        executor=exec_remove_asset,
        differ=differ_remove_asset,
        recorder=record_remove_asset,
    ),
    'remove_directories': InventoryOperator(
        executor=exec_remove_directory,
        differ=differ_remove_directory,
        recorder=record_remove_directory,
    ),
    'remove_generic_file': InventoryOperator(
        executor=partial(generic_executor, lambda x: x[0].unlink()),
        differ=differ_remove_asset,
        recorder=lambda x: dict()  # no operations record for this, not an inventory item
    ),
    'rename_assets': InventoryOperator(
        executor=exec_rename_asset,
        differ=differ_rename_asset,
        recorder=record_rename_asset,
    ),
    'rename_directories': InventoryOperator(
        executor=exec_rename_directory,
        differ=differ_rename_directory,
        recorder=record_rename_directory,
    ),
}
r"""Mapping of Inventory Operation types with the appropriate operators."""


# TODO: Conflict w/ existing operations?
#       operations: raise InvalidInventoryOperationError on conflicts with pending operations,
#       like removing something that is to be created. -> reset() or commit()
# TODO: clear_cache from within commit? What about operations?
class Inventory(object):
    r"""Representation of an inventory of an Onyo repository.

    Provides all functionality necessary to query, modify, create, or remove
    inventory items.

    Attributes
    ----------
    operations
        List of all pending InventoryOperations.
    repo
        The OnyoRepo this Inventory represents.
    """

    def __init__(self,
                 repo: OnyoRepo) -> None:
        r"""Instantiate an ``Inventory`` object based on ``repo``.

        Parameters
        ----------
        repo
            The OnyoRepo to represent.
        """

        self.repo: OnyoRepo = repo
        self.operations: list[InventoryOperation] = []
        self._ignore_for_commit: list[Path] = []

    @property
    def root(self):
        r"""Path to the root inventory directory."""

        return self.repo.git.root

    def reset(self) -> None:
        r"""Discard pending operations."""

        self.operations = []

    def commit(self,
               message: str | None) -> None:
        r"""Execute pending operations and commit the results."""

        # get user message + generate appendix from operations
        # does order matter for execution? Prob.
        # ^  Nope. Fail on conflicts.
        if message is None or not message.strip():
            # If we got no message insert dummy subject line in order to not
            # have the operations record's separator line be the subject.
            message = "[Empty subject]\n"
        paths_to_commit = []
        paths_to_stage = []
        commit_msg = message + "\n\n"

        try:
            for operation in self.operations:
                to_commit, to_stage = operation.execute()
                paths_to_commit.extend(to_commit)
                paths_to_stage.extend(to_stage)

            commit_msg += self.operations_summary()

            # TODO: Actually: staging (only new) should be done in execute. committing is then unified
            self.repo.commit(set(paths_to_commit + paths_to_stage).difference(self._ignore_for_commit), commit_msg)
        finally:
            self.reset()

    def operations_summary(self) -> str:
        r"""Get a textual summary of all operations."""

        summary = "--- Inventory Operations ---\n"
        operations_record = dict()

        for operation in self.operations:
            record_snippets = operation.operator.recorder(repo=self.repo, operands=operation.operands)
            for k, v in record_snippets.items():
                if k not in operations_record:
                    operations_record[k] = v
                else:
                    operations_record[k].extend(v)

        for title, snippets in operations_record.items():
            # Note, for pyre exception: `deduplicate` returns None,
            # if None was passed to it. This should never happen here.
            summary += title + ''.join(
                sorted(line for line in deduplicate(snippets)))  # pyre-ignore[16]

        return summary

    def diff(self) -> Generator[str, None, None]:
        r"""Yield the textual diffs of all operations."""

        for operation in self.operations:
            yield from operation.diff()

    def operations_pending(self) -> bool:
        r"""Return whether there's something to commit."""

        # Note: Seems superfluous now (operations is a list rather than dict of lists)
        return bool(self.operations)

    def _get_pending_assets(self) -> list[str]:
        r"""Get Paths of assets that are to be created by pending operations."""

        # TODO: Inventory methods should check this in addition to Path.exists().
        #       The differs/executors/recorders already generate this
        #       information. Find a way to query that w/o executing in a
        #       structured way. Ideally, we should also account for paths that
        #       are being removed by pending operations and therefore are "free
        #       to use" for operations added to the queue. See issue #546.
        assets = []
        for op in self.operations:
            if op.operator == OPERATIONS_MAPPING['new_assets']:
                assets.append(op.operands[0].get('onyo.path.absolute'))  # TODO: onyo.path.file?
            elif op.operator == OPERATIONS_MAPPING['rename_assets']:
                assets.append(op.operands[1])

        return assets

    def _get_pending_dirs(self) -> list[Path]:
        r"""Get Paths of directories that are to be created by pending operations."""

        # TODO: Currently used within `rename_directory` to allow for
        #       move+rename. This needs enhancement/generalization (check for
        #       removed ones as well, etc.). See issue #546.

        dirs = []
        for op in self.operations:
            if op.operator == OPERATIONS_MAPPING['new_directories']:
                dirs.append(op.operands[0])
            elif op.operator == OPERATIONS_MAPPING['move_directories']:
                dirs.append(op.operands[1] / op.operands[0].name)

        return dirs

    def _get_pending_removals(self,
                              mode: Literal['assets', 'dirs', 'all'] = 'all'
                              ) -> list[Item]:
        r"""Get Items that are to be removed by pending operations.

        Parameters
        ----------
        mode
            Which pending removals to consider.
        """

        # TODO: Just like `_get_pending_assets` and `_get_pending_dirs`, this
        #       needs to be replaced by a more structured way of assessing
        #       what's in the queue. See issue #546.

        paths = []
        operators = []
        if mode in ['assets', 'all']:
            operators.append(OPERATIONS_MAPPING['remove_assets'])
        if mode in ['dirs', 'all']:
            operators.append(OPERATIONS_MAPPING['remove_directories'])
        if mode == 'all':
            operators.append(OPERATIONS_MAPPING['remove_generic_file'])
        for op in self.operations:
            if op.operator in operators:
                paths.append(op.operands[0])

        return paths

    #
    # Operations
    #

    def _add_operation(self,
                       name: str,
                       operands: tuple) -> InventoryOperation:
        r"""Helper to register an operation."""

        op = InventoryOperation(operator=OPERATIONS_MAPPING[name],
                                operands=operands,
                                repo=self.repo)
        self.operations.append(op)

        return op

    def add_asset(self,
                  asset: ItemSpec) -> list[InventoryOperation]:
        r"""Create an asset.

        Parameters
        ----------
        asset
            The Item to create as an asset.

        Raises
        ------
        ValueError
            ``item['onyo.path.absolute']`` cannot be generated, is invalid, or
            the destination already exists.
        """

        # TODO: what if I call this with a modified (possibly moved) asset?
        # -> check for conflicts and raise InvalidInventoryOperationError("something about either commit first or reset")
        operations = []
        path = None

        asset = Item(asset, repo=self.repo)

        self.raise_empty_keys(asset)
        # ### generate stuff - TODO: function - reuse in modify_asset
        if asset.get('serial') == 'faux':
            # TODO: RF this into something that gets a faux serial at a time. This needs to be done
            #       accounting for pending operations in the Inventory.
            asset['serial'] = self.get_faux_serials(num=1).pop()
        self.raise_required_key_empty_value(asset)

        if asset.get('onyo.is.directory', False):
            # 'onyo.path.absolute' needs to be given, if this is about an already existing dir.
            path = asset.get('onyo.path.absolute')
        if path is None:
            # Otherwise, a 'onyo.path.parent' to create the asset in is expected as with
            # any other asset.
            path = asset['onyo.path.absolute'] = self.root / asset['onyo.path.parent'] / self.generate_asset_name(asset)
        if not path:
            raise ValueError("Unable to determine asset path")
        assert isinstance(asset, Item)
        asset.repo = self.repo

        # ### validate - TODO: function - reuse in modify_asset
        if self.repo.is_asset_path(path):
            raise ValueError(f"Asset {path} already exists.")
            # Note: We may want to reconsider this case.
            # Shouldn't there be a way to write files (or asset dirs) directly and then add them as new assets?
        if not self.repo.is_inventory_path(path):
            raise ValueError(f"{str(path)} is not a valid asset path.")
        if path in self._get_pending_assets():
            raise ValueError(f"Asset '{path}' is already pending to be created. Multiple assets cannot be stored at the same path.")

        if asset.get('onyo.is.directory', False):
            if self.repo.is_inventory_dir(path):
                # We want to turn an existing dir into an asset dir.
                operations.extend(self.rename_directory(
                    self.get_item(path),  # get the existing dir, rather than the to-be-asset
                    self.generate_asset_name(asset))
                )
                # Temporary hack: Adjust the asset's path to the renamed one.
                # TODO: Actual solution: This entire method must not be based on the dict's 'onyo.path.absolute', but
                #       'onyo.path.parent' + generated name. This ties in with pulling parts of `onyo_new` in here.
                asset['onyo.path.absolute'] = path.parent / self.generate_asset_name(asset)
            else:
                # The directory does not yet exist.
                operations.extend(self.add_directory(Item(path, repo=self.repo)))
        elif not self.repo.is_inventory_dir(path.parent):
            operations.extend(self.add_directory(Item(path.parent, repo=self.repo)))

        # HACK: regenerate the relative path when it's set, just in case we're
        #       operating on a new asset that is a clone.
        if asset.get('onyo.path.relative', False):
            asset['onyo.path.relative'] = asset['onyo.path.relative'].parent / self.generate_asset_name(asset)

        # record operation
        operations.append(self._add_operation('new_assets', (asset,)))
        return operations

    def add_directory(self,
                      item: Item) -> list[InventoryOperation]:
        r"""Create a directory or convert an Asset File to an Asset Directory.

        Parameters
        ----------
        item
            The Item to make a directory of.

        Raises
        ------
        NoopError
            ``item['onyo.path.absolute']`` is already a directory.
        ValueError
            ``item['onyo.path.absolute']`` is invalid.
        """

        path = item['onyo.path.absolute']
        operations = []

        if not self.repo.is_inventory_path(path):
            raise ValueError(f"{path} is not a valid inventory path.")
        # TODO: The following conditions aren't entirely correct yet.
        #       Address with issue #546.
        if self.repo.is_inventory_dir(path):
            raise NoopError(f"{path} already is an inventory directory.")
        if not self.repo.is_asset_path(path) and path.exists() and not path.is_dir():
            # path is an existing file or symlink that is not an asset - can't do.
            raise ValueError(f"{path} already exists and is not a directory.")

        operations.append(self._add_operation('new_directories', (path,)))
        operations.extend([self._add_operation('new_directories', (p,))
                           for p in path.parents
                           if self.root in p.parents and
                           not self.repo.is_inventory_dir(p) and
                           p not in self._get_pending_dirs()])

        return operations

    def remove_asset(self,
                     asset: Item) -> list[InventoryOperation]:
        r"""Remove an asset.

        Parameters
        ----------
        asset
            Asset Item to remove.

        Raises
        ------
        NotAnAssetError
            ``asset`` is not an asset.
        """

        path = asset.get('onyo.path.absolute')
        if path in [a['onyo.path.absolute'] for a in self._get_pending_removals(mode='assets')]:
            ui.log_debug(f"{path} already queued for removal.")
            # TODO: Consider NoopError when addressing #546.
            return []

        if not self.repo.is_asset_path(path):
            raise NotAnAssetError(f"No such asset: {path}")

        return [self._add_operation('remove_assets', (asset,))]

    def move_asset(self,
                   src: Item,
                   dst: Item) -> list[InventoryOperation]:
        r"""Move an asset to a new parent directory.

        To rename an asset under the same parent, see :py:func:`rename_asset`.

        Parameters
        ----------
        src
            The Path to move.
        dst
            The absolute Path of the new parent directory.

        Raises
        ------
        NotAnAssetError
            ``asset`` is not an asset.
        ValueError
            ``dst`` is the same parent, the target already exists, or
            ``dst`` would be an invalid location.
        """

        if not src['onyo.is.asset']:
            raise NotAnAssetError(f"No such asset: {src['onyo.path.absolute']}.")
        if src['onyo.path.parent'] == dst['onyo.path.relative']:
            # TODO: Instead of raise could be a silent noop.
            raise ValueError(f"Cannot move {src['onyo.path.absolute']}: "
                             f"Destination {dst['onyo.path.absolute']} is the current location.")
        if not dst['onyo.is.directory'] and dst['onyo.path.absolute'] not in self._get_pending_dirs():
            raise ValueError(f"Cannot move {src['onyo.path.absolute']}: "
                             f"Destination {dst['onyo.path.absolute']} is not an inventory directory.")
        target = dst['onyo.path.absolute'] / src['onyo.path.name']
        if target.exists():
            raise ValueError(f"Target {str(target)} already exists.")

        return [self._add_operation('move_assets', (src['onyo.path.absolute'], dst['onyo.path.absolute']))]

    def rename_asset(self,
                     asset: Item) -> list[InventoryOperation]:
        r"""Rename an asset to a new name under the same parent.

        This renames an asset under the same parent. To move to a different
        parent directory, see :py:func:`move_asset`.

        The asset name is automatically generated by :py:func:`generate_asset_name`.
        It cannot be manually set.

        Parameters
        ----------
        asset
            Item to rename.

        Raises
        ------
        NoopError
            Rename would result in the same name.
        ValueError
            ``asset`` is not an asset, the destination already exists, or the
            destination is already pending to be created.
        """

        path = asset.get('onyo.path.absolute')
        if not self.repo.is_asset_path(path):
            raise ValueError(f"No such asset: {path}")

        generated_name = self.generate_asset_name(asset)
        if path.name == generated_name:
            raise NoopError(f"Cannot rename asset {path.name}: This is already its name.")

        destination = path.parent / generated_name
        if destination in self._get_pending_assets():
            raise ValueError(f"Asset '{destination}' is already pending to be created. Multiple assets cannot be stored at the same path.")
        if destination.exists():
            raise ValueError(f"Cannot rename asset {path.name} to {destination}. Already exists.")

        return [self._add_operation('rename_assets', (path, destination))]

    def modify_asset(self,
                     asset: Item,
                     new_asset: Item) -> list[InventoryOperation]:
        r"""Modify an asset.

        Parameters
        ----------
        asset
            Original asset Item to modify.
        new_asset
            New asset Item to apply to ``asset``.

        Raises
        ------
        NoopError
            No modifications would result from applying ``new_asset`` to
            ``asset``.
        ValueError
            ``asset`` is not an asset, or ``new_asset`` changes read-only
            pseudo-keys.
        """

        operations = []
        path = asset.get('onyo.path.absolute')
        if not self.repo.is_asset_path(path):
            raise ValueError(f"No such asset: {path}")

        # Cannot change the path. Move is a different operation, and the asset
        # name is derived from content.
        if new_asset['onyo.path.absolute'] is not None and \
                new_asset['onyo.path.absolute'] != asset['onyo.path.absolute']:
            raise ValueError("A change in 'onyo.path.absolute' must not be set in an asset modification.")

        self.raise_empty_keys(new_asset)
        # ### generate stuff - TODO: function - reuse in add_asset
        if new_asset.get('serial') == 'faux':
            # TODO: RF this into something that gets a faux serial at a time. This needs to be done
            #       accounting for pending operations in the Inventory.
            new_asset['serial'] = self.get_faux_serials(num=1).pop()
        self.raise_required_key_empty_value(new_asset)

        # We keep the old path - if it needs to change, this will be done by a rename operation down the road
        new_asset['onyo.path.absolute'] = path
        if asset == new_asset:
            raise NoopError

        # If a change in is.directory is implied, do this first:
        if asset.get("onyo.is.directory", False) != new_asset.get("onyo.is.directory", False):
            # remove or add dir aspect from/to asset
            ops = self.add_directory(asset) \
                    if new_asset.get("onyo.is.directory", False) \
                    else self.remove_directory(asset)
            operations.extend(ops)

            # If no change in non-pseudo-keys, do not record a modify_assets operation
            if all(asset.get(k) == new_asset.get(k)
                   for k in [a for a in asset.keys()] + [b for b in new_asset.keys()]
                   if k not in PSEUDO_KEYS):
                return operations

        operations.append(self._add_operation('modify_assets', (asset, new_asset)))

        # new_asset has the same 'path' at this point, regardless of potential renaming.
        # We modify the content in place and only then perform a potential rename.
        # Otherwise, we'd move the old asset and write the modified one to the old place or
        # write an entirely new one w/o a git-trackable relation to the old one.
        try:
            operations.extend(self.rename_asset(new_asset))
        except NoopError:
            # modification did not result in a rename
            pass

        return operations

    def remove_directory(self,
                         item: Item,
                         recursive: bool = True) -> list[InventoryOperation]:
        r"""Remove a directory or convert an Asset Directory to a File.

        Parameters
        ----------
        item
            The Item to remove as a directory.
        recursive
            Recursively remove items within ``item``.

        Raises
        ------
        InvalidInventoryOperationError
            ``item['onyo.path.absolute']`` is invalid.
        InventoryDirNotEmpty
            ``item['onyo.path.absolute']`` has children on the filesystem.
        NoopError
            ``item['onyo.path.absolute']`` is already an Asset File.
        """

        if item['onyo.path.absolute'] in [d['onyo.path.absolute'] for d in self._get_pending_removals(mode='dirs')]:
            ui.log_debug(f"{item['onyo.path.absolute']} already queued for removal")
            # TODO: Consider NoopError when addressing #546.
            return []
        if item['onyo.path.absolute'] == self.root:
            raise InvalidInventoryOperationError("Can't remove inventory root.")
        if item['onyo.is.asset'] and not item['onyo.is.directory']:
            raise NoopError(f"{item['onyo.path.absolute']} is already an Asset File.")
        if not item['onyo.is.directory']:
            raise InvalidInventoryOperationError(f"Not an inventory directory: {item['onyo.path.absolute']}")

        operations = []
        for p in item['onyo.path.absolute'].iterdir():
            if p.name in [ANCHOR_FILE_NAME, ASSET_DIR_FILE_NAME]:
                # These files belong to `item` and are handled with it already.
                continue
            if not recursive:
                raise InventoryDirNotEmpty(f"Directory {item['onyo.path.absolute']} not empty.\n")

            p_item = self.get_item(p)
            if p_item['onyo.is.asset']:
                operations.extend(self.remove_asset(p_item))
            if p_item['onyo.is.directory']:
                operations.extend(self.remove_directory(p_item))

        operations.append(self._add_operation('remove_directories', (item,)))

        return operations

    def move_directory(self,
                       src: Item,
                       dst: Item) -> list[InventoryOperation]:
        r"""Move a directory to a new parent directory.

        To rename a directory under the same parent, see :py:func:`rename_directory`.

        Parameters
        ----------
        src
            The Item to move.
        dst
            The new parent directory.

        Raises
        ------
        InvalidInventoryOperationError
            ``src`` and ``dst`` share the same parent.
        ValueError
            ``src`` is not an inventory directory, the target already exists, or
            ``dst`` would be an invalid location.
        """

        if not src['onyo.is.directory']:
            raise ValueError(f"Source is not an inventory directory: {src['onyo.path.absolute']}")
        if not dst['onyo.is.directory'] and dst['onyo.path.absolute'] not in self._get_pending_dirs():
            raise ValueError(f"Destination is not an inventory directory: {dst['onyo.path.absolute']}")
        if src['onyo.path.parent'] == dst['onyo.path.relative']:
            raise InvalidInventoryOperationError(
                f"Cannot move {src['onyo.path.absolute']} -> {dst['onyo.path.absolute']}. Consider renaming instead."
            )
        if (dst['onyo.path.absolute'] / src['onyo.path.name']).exists():
            raise ValueError(f"Target {dst['onyo.path.absolute'] / src['onyo.path.name']} already exists.")

        return [self._add_operation('move_directories', (src['onyo.path.absolute'], dst['onyo.path.absolute']))]

    def rename_directory(self,
                         src: Item,
                         dst: str | Path) -> list[InventoryOperation]:
        r"""Rename a directory to a new name under the same parent.

        This renames a non-asset directory under the same parent. To move to a
        different parent directory, see :py:func:`move_directory`. To rename an
        asset (including an Asset Directory), see :py:func:`modify_asset` and
        :py:func:`rename_asset`.

        Parameters
        ----------
        src
            The Item to rename.
        dst
            The new name or an absolute Path to the new destination.

        Raises
        ------
        InvalidInventoryOperationError
            ``src`` and ``dst`` do not share the same parent.
        NotADirError
            ``src`` is not a non-asset directory.
        NoopError
            Rename would result in the same name.
        ValueError
            ``src`` is not an inventory directory, ``dst`` already exists, or
            ``dst`` would be an invalid location.
        """

        if isinstance(dst, str):
            dst = src['onyo.path.absolute'].parent / dst

        # can't rename an asset or template
        if src['onyo.is.asset'] or src['onyo.is.template']:
            raise NotADirError("Cannot rename an asset or template.")
        # must be an inventory directory
        if not src['onyo.is.directory'] and src['onyo.path.absolute'] not in self._get_pending_dirs():
            raise ValueError(f"Not an inventory directory: {src['onyo.path.absolute']}")
        # we only rename, not move and rename
        if src['onyo.path.absolute'].parent != dst.parent:
            raise InvalidInventoryOperationError(f"Cannot rename to a different parent directory: {src['onyo.path.absolute']} -> {dst}")
        # sanity check the destination
        if not self.repo.is_inventory_path(dst):
            raise ValueError(f"{dst} is not a valid inventory directory.")
        # can't rename to self
        if src['onyo.path.name'] == dst.name:
            raise NoopError(f"Cannot rename directory {src['onyo.path.absolute']}. This is already its name.")
        # destination must be available
        if dst.exists():
            raise ValueError(f"{dst} already exists.")

        return [self._add_operation('rename_directories', (src['onyo.path.absolute'], dst))]

    #
    # non-operation methods
    #
    def get_item(self,
                 path: Path) -> Item:
        r"""Get the ``Item`` of ``path``.

        Parameters
        ----------
        path
            Path to get as an Item.
        """

        return Item(path, self.repo)

    def get_items(self,
                  include: Iterable[Path] | None = None,
                  exclude: Iterable[Path] | Path | None = None,
                  depth: int | None = 0,
                  match: list[Callable[[Item], bool]] | list[list[Callable[[Item], bool]]] | None = None,
                  types: list[Literal['assets', 'directories']] | None = None,
                  intermediates: bool = True
                  ) -> Generator[Item, None, None] | filter:
        r"""Yield all Items matching paths and filters.

        All keys, both on-disk YAML and :py:data:`onyo.lib.pseudokeys.PSEUDO-KEYS`,
        can be matched. Dictionary subkeys are addressed using a period (e.g.
        ``model.name``).

        Parameters
        ----------
        include
            Paths under which to look for Items. Default is inventory root.

            Passed to :py:func:`onyo.lib.onyo.OnyoRepo.get_item_paths`.
        exclude
            Paths to exclude (i.e. Items underneath will not be returned).

            Passed to :py:func:`onyo.lib.onyo.OnyoRepo.get_item_paths`.
        depth
            Number of levels to descend into the directories specified by
            ``include``. A depth of ``0`` descends recursively without limit.

            Passed to :py:func:`onyo.lib.onyo.OnyoRepo.get_item_paths`.
        match
            Callables suited for use with builtin :py:func:`filter`. They are
            passed an :py:class:`onyo.lib.items.Item` and are expected to return
            a ``bool``.

            Within a list of Callables, all must return True for an Item to
            match. When multiple lists are passed, only one list of Callables
            must match for an Item to match (e.g. each list of Callables is
            connected with a logical ``or``).
        types
            Types of inventory items to consider. Equivalent to
            ``onyo.is.asset=True`` and ``onyo.is.directory=True``.
            Default is ``['assets']``.

            Passed to :py:func:`onyo.lib.onyo.OnyoRepo.get_item_paths`.
        intermediates
            Return intermediate directory items. If ``False``, the only directories
            explicitly contained in the returned list are leaves.
        """

        depth = 0 if depth is None else depth

        match = [[]] if match is None else match
        match = [match] if isinstance(match[0], Callable) else match  # pyre-ignore [9]

        for p in self.repo.get_item_paths(include=include,
                                          exclude=exclude,
                                          depth=depth,
                                          types=types,
                                          intermediates=intermediates):
            try:
                item = self.get_item(p)
                # check against filters
                if any([all([f(item) for f in m]) for m in match]):  # pyre-ignore [16]
                    yield item

            except NotAnAssetError as e:
                # report the error, and proceed
                ui.error(e)

    def get_templates(self,
                      template: Path | None,
                      recursive: bool = False) -> Generator[ItemSpec, None, None]:
        r"""Get templates as Items.

        template:
            Path to generate a template from. If relative, this is interpreted
            as relative to the repository's template dir.
        recursive:
            Recursive into template directories.
        """
        yield from self.repo.get_templates(template, recursive=recursive)

    def generate_asset_name(self,
                            asset: ItemSpec) -> str:
        r"""Generate an ``asset``'s file or directory name.

        The asset name format is defined by the configuration
        ``onyo.assets.name-format``.

        Parameters
        ----------
        asset
            Asset Item to generate the name for.

        Raises
        ------
        ValueError
            The configuration 'onyo.assets.name-format' is missing or ``asset``
            does not contain all keys/values needed to generate the asset name.
        """

        config_str = self.repo.get_config("onyo.assets.name-format")
        if not config_str:
            raise ValueError("Missing config 'onyo.assets.name-format'.")

        # Replace key references so that the same dot notation as in CLI works, while actual
        # format-language features using the dot work as well.
        # Example: config string: "{some.more:.3}"
        #          results in : "{asset[some.more]:.3}"
        for name in self.repo.get_asset_name_keys():
            config_str = config_str.replace(f"{{{name}", f"{{asset[{name}]")

        try:
            name = config_str.format(asset=asset)
        except KeyError as e:
            raise ValueError(f"Asset missing value for required field {str(e)}.") from e

        return name

    def get_faux_serials(self,
                         num: int = 1,
                         length: int = 8) -> set[str]:
        r"""Generate a set of unique faux serials.

        The generated faux serials are unique within the set and repository.

        The minimum serial length of 5 offers a serial space of 36^5 (~60.5
        million). That is (arbitrarily) determined to be the highest acceptable
        risk of collisions between independent checkouts of a repo generating
        serials at the same time.

        Parameters
        ----------
        num
            Number of serials to generate.
        length
            String length of the serials to generate. Must be >= 5.

        Raises
        ------
        ValueError
            ``num`` or ``length`` is invalid.
        """

        import random
        import string

        if length < 5:
            raise ValueError('The length of faux serial numbers must be >= 5.')
        if num < 1:
            raise ValueError('The number of faux serial numbers must be >= 1.')

        alphanum = string.ascii_uppercase + string.digits
        faux_serials = set()
        # TODO: This split actually puts the entire filename in the set if there's no "faux".
        repo_faux_serials = {str(x.name).split('faux')[-1] for x in self.repo.asset_paths}

        while len(faux_serials) < num:
            serial = ''.join(random.choices(alphanum, k=length))
            if serial not in repo_faux_serials:
                faux_serials.add(f'faux{serial}')

        return faux_serials

    def raise_required_key_empty_value(self,
                                       asset: ItemSpec) -> None:
        r"""Raise if ``asset`` has an empty value for a required key.

        A validation helper. This checks only asset name keys.

        Parameters
        ----------
        asset
            The asset Item to check.

        Raises
        ------
        ValueError
            A required key has an empty value.
        """

        if any(key not in asset or asset[key] is None or not str(asset[key]).strip()
               for key in self.repo.get_asset_name_keys()):
            raise ValueError(f"Required asset keys ({', '.join(self.repo.get_asset_name_keys())})"
                             f" must not have empty values.")

    def raise_empty_keys(self,
                         asset: ItemSpec) -> None:
        r"""Raise if ``asset`` has empty keys.

        A validation helper.

        Parameters
        ----------
        asset
            The asset Item to check.
        """

        if any(not k or not str(k).strip() or k == 'None' for k in asset.keys()):
            # Note, that ItemSpec.keys() delivers strings (and has to).
            # Hence, `None` as a key would show up here as 'None'.
            raise ValueError("Keys are not allowed to be empty or None-values.")

    def get_history(self,
                    path: Path | None = None,
                    n: int | None = None) -> Generator[UserDict, None, None]:
        r"""Yield the history of Inventory Operations for a path.

        Parameters
        ----------
        path
            The Path to get the history of. Defaults to the repo root.
        n
            Limit history to ``n`` commits. ``None`` for no limit (default).
        """

        yield from self.repo.get_history(path, n)
