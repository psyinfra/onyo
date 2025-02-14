from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.items import Item

if TYPE_CHECKING:
    from typing import Callable


def exec_new_assets(repo: OnyoRepo,
                    operands: tuple[Item]
                    ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'new_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Asset to create.
    """

    # NOTE: No need to implicitly create parent dirs. That is done previously in
    #       its own operation.
    asset = operands[0]
    repo.write_asset_content(asset)  # TODO: a = ...; reassignment for potential updates on metadata
    path = asset.get('onyo.path.absolute')

    return [path], [path]


def exec_new_directories(repo: OnyoRepo,
                         operands: tuple[Path]
                         ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'new_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Path of directory to create.
    """

    p: Path = operands[0]
    asset = dict()
    # This may be an asset file that needs to be turned into an asset dir:
    turn_asset_dir = p.is_file() and repo.is_asset_path(p)
    if turn_asset_dir:
        asset = Item(p, repo=repo)
        p.unlink()
    paths = repo.mk_inventory_dirs(p)
    if turn_asset_dir:
        asset['onyo.is.directory'] = True
        repo.write_asset_content(asset)
        paths.append(p / OnyoRepo.ASSET_DIR_FILE_NAME)

    return paths, paths


def exec_remove_assets(repo: OnyoRepo,
                       operands: tuple[Item]
                       ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'remove_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Asset to remove.
    """

    p: Path = operands[0].get('onyo.path.absolute')
    paths = []

    if p.is_dir():
        # we were told p is an asset. It's also a dir, ergo an asset dir
        paths.append(p / OnyoRepo.ASSET_DIR_FILE_NAME)
    else:
        paths = [p]

    for p in paths:
        # Missing_`ok=True`, because several operations may want to remove the
        # same thing. That's ok.
        # TODO: Reconsider w/ #546
        p.unlink(missing_ok=True)

    return paths, []


def exec_remove_directories(repo: OnyoRepo,
                            operands: tuple[Item]
                            ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'remove_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Directory to remove.
    """

    p: Path = operands[0]['onyo.path.absolute']
    paths = []

    is_asset_dir = (p / OnyoRepo.ASSET_DIR_FILE_NAME).exists()  # required after dir was removed, therefore store
    anchor = p / repo.ANCHOR_FILE_NAME
    anchor.unlink()
    paths.append(anchor)

    if is_asset_dir:
        asset = Item(p, repo=repo)
        paths.append(asset['onyo.path.file'])
        asset['onyo.path.file'].unlink()

    p.rmdir()
    if is_asset_dir:
        asset['onyo.is.directory'] = False  # pyre-ignore[61]  No, this is not "not always defined".
        repo.write_asset_content(asset)  # pyre-ignore[61]
        paths.append(p)  # TODO: Does this need staging? Don't think so, but make sure.

    return paths, []


def _mover(src: Path,
           dst: Path) -> list[Path]:
    r"""Helper for move_{assets,directories}() executors.

    Parameters
    ----------
    src
        Absolute Path of source location.
    dst
        Absolute Path of destination parent.
    """

    src.rename(dst / src.name)
    return [src, dst / src.name]


def exec_move_assets(repo: OnyoRepo,
                     operands: tuple[Path, Path]
                     ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'move_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination parent.
    """

    return _mover(operands[0], operands[1]), []


def exec_move_directories(repo: OnyoRepo,
                          operands: tuple[Path, Path]
                          ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'move_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination parent.
    """

    return _mover(operands[0], operands[1]), []


def _renamer(src: Path,
             dst: Path) -> list[Path]:
    r"""Helper for rename_{assets,directories}() executors.

    Parameters
    ----------
    src
        Absolute Path of source location.
    dst
        Absolute Path of destination location.
    """

    src.rename(dst)
    return [src, dst]


def exec_rename_directories(repo: OnyoRepo,
                            operands: tuple[Path, Path]
                            ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'rename_directories' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination.
    """

    return _renamer(operands[0], operands[1]), []


def exec_rename_assets(repo: OnyoRepo,
                       operands: tuple[Path, Path]
                       ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'rename_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Absolute Paths of the source and destination.
    """

    return _renamer(operands[0], operands[1]), []


def exec_modify_assets(repo: OnyoRepo,
                       operands: tuple[Item, Item]
                       ) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'modify_assets' operation.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    repo
        Onyo repository to operate on.
    operands
        Items of the original and updated asset.
    """

    # expected: (Asset, Asset)
    new = operands[1]
    repo.write_asset_content(new)
    return [new['onyo.path.absolute']], []


def generic_executor(func: Callable,
                     repo: OnyoRepo,
                     operands: tuple
                     ) -> tuple[list[Path], list[Path]]:
    r"""Executor for simple FS operations on non-inventory files.

    Not intended for direct use. It is called from an Operator, which is assumed
    to have validated all input passed to this (trusting) executor.

    Returns two lists:
    1) Paths to be committed 2) Paths to be staged (not previously tracked)

    Parameters
    ----------
    func
        Function to pass ``operands`` to.
    repo
        Onyo repository to operate on.
    operands
        Operands to pass to ``func``.
    """

    func(operands)
    return [operands[0]], []
