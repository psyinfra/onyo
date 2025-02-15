from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    from onyo.lib.items import Item


def _record_item(repo: OnyoRepo,
                 item: Path | Item) -> str:
    r"""Helper for ``{new,modify,remove}_{asset,directory}()`` recorders.

    Parameters
    ----------
    item
        Absolute Path or Item of target.
    """

    path = item if isinstance(item, Path) else item['onyo.path.absolute']

    return f"- {path.relative_to(repo.git.root).as_posix()}\n"


def _record_move(repo: OnyoRepo,
                 src: Path | Item,
                 dst: Path) -> str:
    r"""Helper for ``move_{asset,directory}()`` recorders.

    Parameters
    ----------
    src
        Absolute Path or Item of source location.
    dst
        Absolute Path of destination parent.
    """

    # This expects `dst` to be the dir to move src into, rather than already
    # containing the `src.name` at the destination.
    src_path = src if isinstance(src, Path) else src['onyo.path.absolute']
    dst_path = (dst / src_path.name).relative_to(repo.git.root).as_posix()
    src_path = src_path.relative_to(repo.git.root).as_posix()

    return f"- {src_path} -> {dst_path}\n"


def _record_rename(repo: OnyoRepo,
                   src: Path | Item,
                   dst: Path) -> str:
    r"""Helper for ``rename_{asset,directory}()`` recorders.

    Parameters
    ----------
    src
        Absolute Path or Item of source location.
    dst
        Absolute Path of destination location.
    """

    # In contrast to _record_move(), this expects the full target path in `dst`.
    src_path = src if isinstance(src, Path) else src['onyo.path.absolute']
    src_path = src_path.relative_to(repo.git.root).as_posix()
    dst_path = dst.relative_to(repo.git.root).as_posix()

    return f"- {src_path} -> {dst_path}\n"


def record_modify_asset(repo: OnyoRepo,
                        operands: tuple[Item, Item]
                        ) -> dict[str, list[str]]:
    r"""Recorder for the 'modify_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Items of the original and updated asset.
    """

    return {"Modified assets:\n": [_record_item(repo, operands[0])]}


def record_move_asset(repo: OnyoRepo,
                      operands: tuple[Path, Path]
                      ) -> dict[str, list[str]]:
    r"""Recorder for the 'move_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination parent.
    """

    records = {"Moved assets:\n": [_record_move(repo, operands[0], operands[1])]}
    if repo.is_asset_dir(operands[0]):
        # In case of an asset dir, we need to record an operation for both aspects
        records.update({"Moved directories:\n": [_record_move(repo, operands[0], operands[1])]})

    return records


def record_move_directory(repo: OnyoRepo,
                          operands: tuple[Path, Path]
                          ) -> dict[str, list[str]]:
    r"""Recorder for the 'move_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination parent.
    """

    records = {"Moved directories:\n": [_record_move(repo, operands[0], operands[1])]}
    if repo.is_asset_dir(operands[0]):
        # In case of an asset dir, we need to record an operation for both aspects
        records.update({"Moved assets:\n": [_record_move(repo, operands[0], operands[1])]})

    return records


def record_new_asset(repo: OnyoRepo,
                     operands: tuple[Item]
                     ) -> dict[str, list[str]]:
    r"""Recorder for the 'new_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Asset to create.
    """

    return {"New assets:\n": [_record_item(repo, operands[0])]}


def record_new_directory(repo: OnyoRepo,
                         operands: tuple[Path]
                         ) -> dict[str, list[str]]:
    r"""Recorder for the 'new_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Path of directory to create.
    """

    return {"New directories:\n": [_record_item(repo, operands[0])]}


def record_remove_asset(repo: OnyoRepo,
                        operands: tuple[Item]
                        ) -> dict[str, list[str]]:
    r"""Recorder for the 'remove_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Asset to remove.
    """

    return {"Removed assets:\n": [_record_item(repo, operands[0])]}


def record_remove_directory(repo: OnyoRepo,
                            operands: tuple[Item]
                            ) -> dict[str, list[str]]:
    r"""Recorder for the 'remove_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Directory to remove.
    """

    return {"Removed directories:\n": [_record_item(repo, operands[0])]}


def record_rename_asset(repo: OnyoRepo,
                        operands: tuple[Path, Path]
                        ) -> dict[str, list[str]]:
    r"""Recorder for the 'rename_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination.
    """

    records = {"Renamed assets:\n": [_record_rename(repo, operands[0], operands[1])]}
    if repo.is_asset_dir(operands[0]):
        # In case of an asset dir, we need to record an operation for both aspects
        records.update({"Renamed directories:\n": [_record_rename(repo, operands[0], operands[1])]})

    return records


def record_rename_directory(repo: OnyoRepo,
                            operands: tuple[Path, Path]
                            ) -> dict[str, list[str]]:
    r"""Recorder for the 'rename_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) recorder.

    Returns a dict in the format:
    ``key``: title of the Inventory Operations section
    ``value``: list of textual records of Inventory Operations

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination.
    """

    return {"Renamed directories:\n": [_record_rename(repo, operands[0], operands[1])]}
