from __future__ import annotations

from difflib import unified_diff
from typing import TYPE_CHECKING

from onyo.lib.items import Item
from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Generator


def _diff_assets(asset_old: Item,
                 asset_new: Item
                 ) -> Generator[str, None, None]:
    r"""Helper for ``{modify,new}_asset()`` differs.

    Parameters
    ----------
    src
        Absolute Path of source location.
    dst
        Absolute Path of destination parent.
    """

    yield from unified_diff(asset_old.yaml().splitlines(keepends=False),
                            asset_new.yaml().splitlines(keepends=False),
                            fromfile=str(asset_old.get('onyo.path.absolute', '')),
                            tofile=str(asset_new.get('onyo.path.absolute', '')),
                            lineterm="")


def _diff_path_change(src: Path,
                      dst: Path
                      ) -> Generator[str, None, None]:
    r"""Helper for ``{move,rename}_{asset,directory}()`` differs.

    Parameters
    ----------
    src
        Absolute Path of source location.
    dst
        Absolute Path of destination parent.
    """

    yield f"{str(src)} -> {str(dst)}"


def differ_modify_asset(repo: OnyoRepo,
                        operands: tuple[Item, Item]
                        ) -> Generator[str, None, None]:
    r"""Differ for the 'modify_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Items of the original and updated asset.
    """

    yield from _diff_assets(operands[0], operands[1])


def differ_move_asset(repo: OnyoRepo,
                      operands: tuple[Path, Path]
                      ) -> Generator[str, None, None]:
    r"""Differ for the 'move_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination parent.
    """

    yield from _diff_path_change(operands[0], operands[1])


def differ_move_directory(repo: OnyoRepo,
                          operands: tuple[Path, Path]
                          ) -> Generator[str, None, None]:
    r"""Differ for the 'move_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination parent.
    """

    yield from _diff_path_change(operands[0], operands[1])


def differ_new_asset(repo: OnyoRepo,
                     operands: tuple[Item]
                     ) -> Generator[str, None, None]:
    r"""Differ for the 'new_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Asset to create.
    """

    yield from _diff_assets(asset_old=Item({}, repo=repo), asset_new=operands[0])


def differ_new_directory(repo: OnyoRepo,
                         operands: tuple[Path]
                         ) -> Generator[str, None, None]:
    r"""Differ for the 'new_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Path of directory to create.
    """

    yield f"+{str(operands[0])}"


def differ_remove_asset(repo: OnyoRepo,
                        operands: tuple[Item]
                        ) -> Generator[str, None, None]:
    r"""Differ for the 'remove_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Asset to remove.
    """

    yield f"-{operands[0].get('onyo.path.absolute')}"


def differ_remove_directory(repo: OnyoRepo,
                            operands: tuple[Item]
                            ) -> Generator[str, None, None]:
    r"""Differ for the 'remove_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Directory to remove.
    """

    yield f"-{operands[0].get('onyo.path.absolute')}"


def differ_rename_asset(repo: OnyoRepo,
                        operands: tuple[Path, Path]
                        ) -> Generator[str, None, None]:
    r"""Differ for the 'rename_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination.
    """

    yield from _diff_path_change(operands[0], operands[1])


def differ_rename_directory(repo: OnyoRepo,
                            operands: tuple[Path, Path]
                            ) -> Generator[str, None, None]:
    r"""Differ for the 'rename_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) differ.

    Yields the diff of the operation line-by-line.

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination.
    """

    yield from _diff_path_change(operands[0], operands[1])
