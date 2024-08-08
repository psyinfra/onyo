from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.differs import (
    differ_new_assets,
    differ_new_directories,
    differ_modify_assets,
    differ_move_assets,
    differ_move_directories,
    differ_remove_assets,
    differ_remove_directories,
    differ_rename_assets,
    differ_rename_directories,
)
from onyo.lib.exceptions import (
    InvalidInventoryOperationError,
    InventoryDirNotEmpty,
    NoopError,
    NotADirError,
    NotAnAssetError,
)
from onyo.lib.executors import (
    exec_modify_assets,
    exec_move_assets,
    exec_move_directories,
    exec_new_assets,
    exec_new_directories,
    exec_remove_assets,
    exec_remove_directories,
    exec_rename_assets,
    exec_rename_directories,
    generic_executor,
)
from onyo.lib.onyo import OnyoRepo
from onyo.lib.recorders import (
    record_modify_assets,
    record_move_assets,
    record_move_directories,
    record_new_assets,
    record_new_directories,
    record_remove_assets,
    record_remove_directories,
    record_rename_assets,
    record_rename_directories,
)
from onyo.lib.utils import deduplicate
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Callable,
        Generator,
        Literal,
    )


@dataclass
class InventoryOperator:
    executor: Callable
    differ: Callable
    recorder: Callable


@dataclass
class InventoryOperation(object):
    operator: InventoryOperator
    operands: tuple
    repo: OnyoRepo

    def diff(self) -> Generator[str, None, None]:
        yield from self.operator.differ(repo=self.repo, operands=self.operands)

    def execute(self) -> tuple[list[Path], list[Path]]:
        return self.operator.executor(repo=self.repo, operands=self.operands)


OPERATIONS_MAPPING: dict = {'new_directories': InventoryOperator(executor=exec_new_directories,
                                                                 differ=differ_new_directories,
                                                                 recorder=record_new_directories),
                            'new_assets': InventoryOperator(executor=exec_new_assets,
                                                            differ=differ_new_assets,
                                                            recorder=record_new_assets),
                            'remove_assets': InventoryOperator(executor=exec_remove_assets,
                                                               differ=differ_remove_assets,
                                                               recorder=record_remove_assets),
                            'modify_assets': InventoryOperator(executor=exec_modify_assets,
                                                               differ=differ_modify_assets,
                                                               recorder=record_modify_assets),
                            'rename_assets': InventoryOperator(executor=exec_rename_assets,
                                                               differ=differ_rename_assets,
                                                               recorder=record_rename_assets),
                            'remove_directories': InventoryOperator(executor=exec_remove_directories,
                                                                    differ=differ_remove_directories,
                                                                    recorder=record_remove_directories),
                            'move_directories': InventoryOperator(executor=exec_move_directories,
                                                                  differ=differ_move_directories,
                                                                  recorder=record_move_directories),
                            'rename_directories': InventoryOperator(executor=exec_rename_directories,
                                                                    differ=differ_rename_directories,
                                                                    recorder=record_rename_directories),
                            'move_assets': InventoryOperator(executor=exec_move_assets,
                                                             differ=differ_move_assets,
                                                             recorder=record_move_assets),
                            'remove_generic_file': InventoryOperator(
                                executor=partial(generic_executor, lambda x: x[0].unlink()),
                                differ=differ_remove_assets,
                                recorder=lambda x: dict()),  # no operations record for this, not an inventory item.
                            }


# TODO: Conflict w/ existing operations?
#       operations: raise InvalidInventoryOperationError on conflicts with pending operations,
#       like removing something that is to be created. -> reset() or commit()
# TODO: clear_cache from within commit? What about operations?
class Inventory(object):
    r""""""

    def __init__(self, repo: OnyoRepo) -> None:
        self.repo: OnyoRepo = repo
        self.operations: list[InventoryOperation] = []
        self._ignore_for_commit: list[Path] = []

    @property
    def root(self):
        r"""Path to root inventory directory."""
        return self.repo.git.root

    def reset(self) -> None:
        r"""Discard pending operations."""
        self.operations = []

    def commit(self, message: str) -> None:
        r"""Execute and git-commit pending operations."""
        # get user message + generate appendix from operations
        # does order matter for execution? Prob.
        # ^  Nope. Fail on conflicts.
        from os import linesep
        paths_to_commit = []
        paths_to_stage = []
        commit_msg = message + f"{linesep}{linesep}--- Inventory Operations ---{linesep}"
        operations_record = dict()

        try:
            for operation in self.operations:
                to_commit, to_stage = operation.execute()
                paths_to_commit.extend(to_commit)
                paths_to_stage.extend(to_stage)
                record_snippets = operation.operator.recorder(repo=self.repo, operands=operation.operands)
                for k, v in record_snippets.items():
                    if k not in operations_record:
                        operations_record[k] = v
                    else:
                        operations_record[k].extend(v)

            for title, snippets in operations_record.items():
                # Note, for pyre exception: `deduplicate` returns None,
                # if None was passed to it. This should never happen here.
                commit_msg += title + ''.join(
                    sorted(line for line in deduplicate(snippets)))  # pyre-ignore[16]

            # TODO: Actually: staging (only new) should be done in execute. committing is then unified
            self.repo.commit(set(paths_to_commit + paths_to_stage).difference(self._ignore_for_commit), commit_msg)
        finally:
            self.reset()

    def diff(self) -> Generator[str, None, None]:
        for operation in self.operations:
            yield from operation.diff()

    def operations_pending(self) -> bool:
        r"""Returns whether there's something to commit."""
        # Note: Seems superfluous now (operations is a list rather than dict of lists)
        return bool(self.operations)

    def _get_pending_asset_names(self) -> list[str]:
        r"""List of asset names that are targets of pending operations.

        This is extracting paths that would exist if the currently
        pending operations were executed, in order to provide the
        means to check for conflicts.

        Current usecase: When adding/renaming assets, their
        names and must not yet exist - neither committed nor pending.
        """
        # TODO: This needs to be better designed and generalized to
        # include directory paths. Inventory methods need to check this
        # instead of or in addition to something like Path.exists().
        # The differs/executors/recorders already generate this
        # information. Find a way to query that w/o executing in a
        # structured way. Ideally, we should also account for paths
        # that are being removed by pending operations and therefore
        # are "free to use" for operations added to the queue.
        names = []
        for op in self.operations:
            if op.operator == OPERATIONS_MAPPING['new_assets']:
                names.append(op.operands[0].get('path').name)
            elif op.operator == OPERATIONS_MAPPING['rename_assets']:
                names.append(op.operands[1].name)
        return names

    def _get_pending_dirs(self) -> list[Path]:
        r"""Get inventory dirs that would come into existence due to pending operations.

        Extract paths to inventory dirs, that are the anticipated results of pending
        moves and creations.

        Notes
        -----
        Currently used within `rename_directory` to allow for move+rename.
        This needs enhancement/generalization (check for removed ones as well, etc.)

        Returns
        -------
        list of Path
            Inventory dirs about to be created.
        """
        dirs = []
        for op in self.operations:
            if op.operator == OPERATIONS_MAPPING['new_directories']:
                dirs.append(op.operands[0])
            elif op.operator == OPERATIONS_MAPPING['move_directories']:
                dirs.append(op.operands[1] / op.operands[0].name)
        return dirs

    def _get_pending_removals(self,
                              mode: Literal['assets', 'dirs', 'all'] = 'all') -> list[Path]:
        r"""Get paths that are removed by pending operations.

        Parameters
        ----------
        mode
            What pending removals to consider: 'assets' only, 'dirs' only, or 'all'.

        Notes
        -----
        Just like `_get_pending_asset_names` and `_get_pending_dirs`,
        this needs to be replaced by a more structured way of assessing
        what's in the queue. See issue #546.

        Returns
        -------
        list of Path
            To be removed paths.
        """
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

    def _add_operation(self, name: str, operands: tuple) -> InventoryOperation:
        r"""Internal convenience helper to register an operation."""
        op = InventoryOperation(operator=OPERATIONS_MAPPING[name],
                                operands=operands,
                                repo=self.repo)
        self.operations.append(op)
        return op

    def add_asset(self, asset: dict) -> list[InventoryOperation]:
        # TODO: what if I call this with a modified (possibly moved) asset?
        # -> check for conflicts and raise InvalidInventoryOperationError("something about either commit first or rest")
        operations = []
        path = None

        self.raise_empty_keys(asset)
        # ### generate stuff - TODO: function - reuse in modify_asset
        if asset.get('serial') == 'faux':
            # TODO: RF this into something that gets a faux serial at a time. This needs to be done
            #       accounting for pending operations in the Inventory.
            asset['serial'] = self.get_faux_serials(num=1).pop()
        self.raise_required_key_empty_value(asset)
        name = self.generate_asset_name(asset)

        if asset.get('is_asset_directory', False):
            # 'path' needs to be given, if this is about an already existing dir.
            # Otherwise, a 'directory' to create the asset in is expected as with
            # any other asset.
            path = asset.get('path')
        if path is None:
            path = asset['path'] = asset['directory'] / name
        if not path:
            raise ValueError("Unable to determine asset path")

        # ### validate - TODO: function - reuse in modify_asset
        if self.repo.is_asset_path(path):
            raise ValueError(f"Asset {path} already exists.")
            # Note: We may want to reconsider this case.
            # Shouldn't there be a way to write files (or asset dirs) directly and then add them as new assets?
        if not self.repo.is_inventory_path(path):
            raise ValueError(f"{str(path)} is not a valid asset path.")
        if name in self._get_pending_asset_names() + [p.name for p in self.repo.asset_paths]:
            raise ValueError(f"Asset name '{name}' already exists in inventory")

        if asset.get('is_asset_directory', False):
            if self.repo.is_inventory_dir(path):
                # We want to turn an existing dir into an asset dir.
                operations.extend(self.rename_directory(path, self.generate_asset_name(asset)))
                # Temporary hack: Adjust the asset's path to the renamed one.
                # TODO: Actual solution: This entire method must not be based on the dict's 'path', but 'directory' +
                #       generated name. This ties in with pulling parts of `onyo_new` in here.
                asset['path'] = path.parent / self.generate_asset_name(asset)
            else:
                # The directory does not yet exist.
                operations.extend(self.add_directory(path))
        elif not self.repo.is_inventory_dir(path.parent):
            operations.extend(self.add_directory(path.parent))

        # record operation
        operations.append(self._add_operation('new_assets', (asset,)))
        return operations

    def add_directory(self, path: Path) -> list[InventoryOperation]:
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
                           if self.root in p.parents and not self.repo.is_inventory_dir(p)])
        return operations

    def remove_asset(self, asset: dict | Path) -> list[InventoryOperation]:
        path = asset if isinstance(asset, Path) else asset.get('path')
        if path in self._get_pending_removals(mode='assets'):
            ui.log_debug(f"{path} already queued for removal.")
            # TODO: Consider NoopError when addressing #546.
            return []
        if not self.repo.is_asset_path(path):
            raise NotAnAssetError(f"No such asset: {path}")
        return [self._add_operation('remove_assets', (asset,))]

    def move_asset(self, src: Path | dict, dst: Path) -> list[InventoryOperation]:
        if isinstance(src, dict):
            src = Path(src.get('path'))
        if not self.repo.is_asset_path(src):
            raise NotAnAssetError(f"No such asset: {src}.")
        if src.parent == dst:
            # TODO: Instead of raise could be a silent noop.
            raise ValueError(f"Cannot move {src}: Destination {dst} is the current location.")
        if not self.repo.is_inventory_dir(dst) and dst not in self._get_pending_dirs():
            raise ValueError(f"Cannot move {src}: Destination {dst} is not an inventory directory.")
        if (dst / src.name).exists():
            raise ValueError(f"Target {dst / src.name} already exists.")

        return [self._add_operation('move_assets', (src, dst))]

    def rename_asset(self, asset: dict | Path, name: str | None = None) -> list[InventoryOperation]:
        # ??? Do we need that? On the command level it's only accessible via modify_asset.
        # But: A config change is sufficient to make it not actually an asset modification.
        # Also: If we later on want to allow it under some circumstances, it would be good have it as a formally
        #       separate operation already.

        path = Path(asset.get('path')) if isinstance(asset, dict) else asset
        if not self.repo.is_asset_path(path):
            raise ValueError(f"No such asset: {path}")

        # Note: For now we force the asset name (via config) from its content. Hence, `name` is optional and when it's
        #       given it needs to match.
        #       TODO: This may, however, need to go. When rename is implicit, it would need to account for already
        #             registered modify operations. It's easier to not force compliance here, but simply let
        #             modify_asset generate the name and pass it.
        generated_name = self.generate_asset_name(
            asset if isinstance(asset, dict)
            else self.repo.get_asset_content(path)
        )
        if name and name != generated_name:
            raise ValueError(f"Renaming asset {path.name} to {name} is invalid."
                             f"Config 'onyo.assets.name-format' suggests '{generated_name}' as its name.")
        if not name:
            name = generated_name
        if path.name == name:
            raise NoopError(f"Cannot rename asset {name}: This is already its name.")

        destination = path.parent / name
        if name in self._get_pending_asset_names() + [p.name for p in self.repo.asset_paths]:
            raise ValueError(f"Asset name '{name}' already exists in inventory")
        if destination.exists():
            raise ValueError(f"Cannot rename asset {path.name} to {destination}. Already exists.")
        return [self._add_operation('rename_assets', (path, destination))]

    def modify_asset(self, asset: dict | Path, new_asset: dict) -> list[InventoryOperation]:
        operations = []
        path = Path(asset.get('path')) if isinstance(asset, dict) else asset
        if not self.repo.is_asset_path(path):
            raise ValueError(f"No such asset: {path}")
        asset = self.repo.get_asset_content(path) if isinstance(asset, Path) else asset

        # Raise on 'path' key in `new_asset`. It needs to be generated:
        if 'path' in new_asset:
            raise ValueError("Illegal key 'path' in new asset.")  # TODO: Figure better message (or change upstairs)

        self.raise_empty_keys(new_asset)
        # ### generate stuff - TODO: function - reuse in add_asset
        if new_asset.get('serial') == 'faux':
            # TODO: RF this into something that gets a faux serial at a time. This needs to be done
            #       accounting for pending operations in the Inventory.
            new_asset['serial'] = self.get_faux_serials(num=1).pop()
        self.raise_required_key_empty_value(new_asset)
        # We keep the old path - if it needs to change, this will be done by a rename operation down the road
        new_asset['path'] = path

        if asset == new_asset:
            raise NoopError

        # If a change in is_asset_directory is implied, do this first:
        if asset.get("is_asset_directory", False) != new_asset.get("is_asset_directory", False):
            # remove or add dir aspect from/to asset
            ops = self.add_directory(asset["path"]) if new_asset.get("is_asset_directory", False)\
                else self.remove_directory(asset["path"])
            operations.extend(ops)
            # If there is no other change, we should not record a modify_assets operation!
            if all(asset.get(k) == new_asset.get(k)
                   for k in [a for a in asset.keys()] + [b for b in new_asset.keys()]
                   if k != "is_asset_directory"):
                return operations
        operations.append(self._add_operation('modify_assets', (asset, new_asset)))
        # new_asset has the same 'path' at this point, regardless of potential renaming.
        # We modify the content in place and only then perform a potential rename.
        # Otherwise, we'd move the old asset and write the modified one to the old place or
        # write an entirely new one w/o a git-trackable relation to the old one.
        try:
            operations.extend(self.rename_asset(new_asset))
        except NoopError:
            # Modification did not imply a rename
            pass
        return operations

    def remove_directory(self, directory: Path, recursive: bool = True) -> list[InventoryOperation]:
        if directory in self._get_pending_removals(mode='dirs'):
            ui.log_debug(f"{directory} already queued for removal")
            # TODO: Consider NoopError when addressing #546.
            return []
        if directory == self.root:
            raise InvalidInventoryOperationError("Can't remove inventory root.")
        operations = []
        if not self.repo.is_inventory_dir(directory):
            raise InvalidInventoryOperationError(f"Not an inventory directory: {directory}")
        for p in directory.iterdir():
            if not recursive and p.name not in [self.repo.ANCHOR_FILE_NAME, self.repo.ASSET_DIR_FILE_NAME]:
                raise InventoryDirNotEmpty(f"Directory {directory} not empty.")
            try:
                operations.extend(self.remove_asset(p))
                is_asset = True
            except NotAnAssetError:
                is_asset = False
            if p.is_dir():
                operations.extend(self.remove_directory(p))
            elif not is_asset and p.name not in [self.repo.ANCHOR_FILE_NAME, self.repo.ASSET_DIR_FILE_NAME]:
                # Not an asset and not an inventory dir (hence also not an asset dir)
                # implies we have a non-inventory file.
                if p in self._get_pending_removals(mode='all'):
                    ui.log_debug(f"{p} already queued for removal")
                    continue
                operations.append(self._add_operation('remove_generic_file', (p,)))
        operations.append(self._add_operation('remove_directories', (directory,)))
        return operations

    def move_directory(self, src: Path, dst: Path) -> list[InventoryOperation]:
        if not self.repo.is_inventory_dir(src):
            raise ValueError(f"Not an inventory directory: {src}")
        if not self.repo.is_inventory_dir(dst) and dst not in self._get_pending_dirs():
            raise ValueError(f"Destination is not an inventory directory: {dst}")
        if src.parent == dst:
            raise InvalidInventoryOperationError(f"Cannot move {src} -> {dst}. Consider renaming instead.")
        if (dst / src.name).exists():
            raise ValueError(f"Target {dst / src.name} already exists.")
        return [self._add_operation('move_directories', (src, dst))]

    def rename_directory(self, src: Path, dst: str | Path) -> list[InventoryOperation]:
        if not self.repo.is_inventory_dir(src) and src not in self._get_pending_dirs():
            raise ValueError(f"Not an inventory directory: {src}")
        if self.repo.is_asset_dir(src):
            raise NotADirError("Renaming an asset directory must be done via `rename_asset`.")
        if isinstance(dst, str):
            dst = src.parent / dst
        if src.parent != dst.parent:
            raise InvalidInventoryOperationError(f"Cannot rename {src} -> {dst}. Consider moving instead.")
        if not self.repo.is_inventory_path(dst):
            raise ValueError(f"{dst} is not a valid inventory directory.")
        if dst.exists():
            raise ValueError(f"{dst} already exists.")
        name = dst if isinstance(dst, str) else dst.name
        if src.name == name:
            raise NoopError(f"Cannot rename directory {str(src)}: This is already its name.")

        return [self._add_operation('rename_directories', (src, dst))]

    #
    # non-operation methods
    #

    def get_asset(self, path: Path):
        # read and return Asset
        return self.repo.get_asset_content(path)

    def get_assets(self,
                   paths: list[Path] | None = None,
                   depth: int = 0) -> Generator[dict, None, None]:
        r"""Yield all assets under `paths` up to `depth` directory levels.

        Generator, because it needs to read file content. This allows to act upon
        results while they are coming in.

        Parameters
        ----------
        paths
          Paths to look for assets under. Defaults to the root of the inventory.
        depth
          Number of levels to descend into. Must be greater equal 0.
          If 0, descend recursively without limit. Defaults to 0.

        Returns
        -------
        Generator of dict
           All matching assets in the inventory.
        """
        return (self.get_asset(p) for p in self.repo.get_asset_paths(subtrees=paths, depth=depth))

    def get_asset_from_template(self, template: Path | str | None) -> dict:
        # TODO: Possibly join with get_asset (path optional)
        return self.repo.get_template(template)

    def get_assets_by_query(self,
                            paths: list[Path] | None = None,
                            depth: int | None = 0,
                            match: list[Callable[[dict], bool]] | None = None) -> Generator | filter:
        r"""Get assets matching paths and filters.

        Convenience to run the builtin `filter` on all assets retrieved by
        `self.get(paths, depth)` for each callable in `filters`, thus
        combining the filters by a logical AND.

        Parameters
        ----------
        paths
          Paths to look for assets under. Defaults to the root of
          the inventory. Passed to `self.get_assets`.
        depth
          Number of levels to descend into. Must be greater or equal 0.
          If 0, descend recursively without limit. Defaults to 0.
          Passed to `self.get_assets`.
        match
          Callable suitable for the builtin `filter`, when called on a
          list of assets (dictionaries).

        Returns
        -------
        Generator of dict
          All assets found underneath `paths` up to `depth` levels,
          for which all `filters` returned `True`.
        """
        depth = 0 if depth is None else depth
        assets = self.get_assets(paths=paths, depth=depth)
        if match:
            # Remove assets that do not match all filters
            for f in match:
                assets = filter(f, assets)
        return assets

    def asset_paths_available(self, assets: dict | list[dict]) -> None:
        r"""Test whether path used by `assets` are available in the inventory.

        Availability not only requires the path to not yet exist, but also the filename to be unique.

        Raises
        ------
        ValueError
          if any of the paths can not be used for a new asset
        """

        # TODO: Used to test valid asset name first. Do we need that?
        #       Not in context of `new`, because the name is generated.
        paths_to_test = [a.get('path') for a in assets]
        for path in paths_to_test:
            if not path:
                continue  # TODO: raise or ignore?
            if path.exists():
                raise ValueError(f"{str(path)} already exists in inventory")
            if len([p.name for p in paths_to_test if p.name == path.name]) > 1:
                raise ValueError(f"Multiple {path.name} given. Asset names must be unique.")
            if not self.repo.is_inventory_path(path):
                raise ValueError(f"{str(path)} is not a valid asset path.")
            if path.name in [p.name for p in self.repo.asset_paths]:
                raise ValueError(f"Asset name '{path.name}' already exists in inventory.")

    def generate_asset_name(self, asset: dict) -> str:
        config_str = self.repo.get_config("onyo.assets.name-format")
        if not config_str:
            raise ValueError("Missing config 'onyo.assets.name-format'.")
        try:
            name = config_str.format(**asset)  # TODO: Only pass non-pseudo keys?! What if there is no config?
        except KeyError as e:
            raise ValueError(f"Asset missing value for required field {str(e)}.") from e
        return name

    def get_faux_serials(self,
                         length: int = 6,
                         num: int = 1) -> set[str]:
        r"""Generate a unique faux serial.

        Generate a faux serial and verify that it is not used by any other asset
        in the repository. The length of the faux serial must be 4 or greater.

        Returns a set of unique faux serials.
        """
        import random
        import string

        if length < 4:
            # 62^4 is ~14.7 million combinations. Which is the lowest acceptable
            # risk of collisions between independent checkouts of a repo.
            raise ValueError('The length of faux serial numbers must be >= 4.')

        if num < 1:
            raise ValueError('The number of faux serial numbers must be >= 1.')

        alphanum = string.ascii_letters + string.digits
        faux_serials = set()
        # TODO: This split actually puts the entire filename in the set if there's no "faux".
        repo_faux_serials = {str(x.name).split('faux')[-1] for x in self.repo.asset_paths}

        while len(faux_serials) < num:
            serial = ''.join(random.choices(alphanum, k=length))
            if serial not in repo_faux_serials:
                faux_serials.add(f'faux{serial}')

        return faux_serials

    def raise_required_key_empty_value(self, asset: dict) -> None:
        r"""Whether `asset` has an empty value for a required key.

        Validation helper.

        Notes
        -----
        This is currently considering asset name keys only. However,
        proper asset validation with ways to declare other keys
        required is anticipated. This would need to account for those
        as well.
        """
        if any(v is None or not str(v).strip()
               for k, v in asset.items()
               if k in self.repo.get_asset_name_keys()):
            raise ValueError(f"Required asset keys ({', '.join(self.repo.get_asset_name_keys())})"
                             f" must not have empty values.")

    def raise_empty_keys(self, asset: dict) -> None:
        r"""Whether `asset` has empty keys.

        Validation helper
        """
        if any(not k or not str(k).strip() for k in asset.keys()):
            raise ValueError("Keys are not allowed to be empty or None-values.")
