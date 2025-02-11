from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.items import Item

if TYPE_CHECKING:
    from typing import Callable

# Executors signature: (repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]
#                      first returned list are the paths that need to be committed
#                      second list are the paths that need to be staged (not previously tracked)

# Attention! No input validation in executors -> document "not intended for direct use"
# Those callables are to be registered with operators. Operations have to make sure to deliver
# valid objects. We don't want to issue a ton of stat calls just to validate the same paths
# throughout every layer of onyo over and over.


def exec_new_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'new_asset' operation

    Parameters
    ----------
    repo
      Onyo repository to operate on
    operands
      Each item of the list is a tuple of operation operands.
      Here a single item per tuple is expected: The to-be-added `Asset`

    Returns
    -------
    list of Path
      paths to the newly added assets
    """
    # Note: No need to account for implicitly to create dirs herein. That would be its own operation done before.
    asset = operands[0]
    repo.write_asset_content(asset)  # TODO: a = ...; reassignment for potential updates on metadata
    path = asset.get('onyo.path.absolute')
    return [path], [path]


def exec_new_directories(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    r"""Executor for the 'new_directory' operation
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


def exec_remove_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    p = operands[0] if isinstance(operands[0], Path) else operands[0].get('onyo.path.absolute')
    paths = []
    if p.is_dir():
        # we were told p is an asset. It's also a dir, ergo an asset dir
        paths.append(p / OnyoRepo.ASSET_DIR_FILE_NAME)
    else:
        paths = [p]
    for p in paths:
        # missing_ok=True, b/c several operations may want to remove the same thing. No reason to fail here.
        # TODO: Reconsider w/ #546
        p.unlink(missing_ok=True)
    return paths, []


def exec_remove_directories(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    paths = []
    p = operands[0]['onyo.path.absolute']
    is_asset_dir = (p / OnyoRepo.ASSET_DIR_FILE_NAME).exists()  # required after dir was removed, therefore store
    anchor = p / repo.ANCHOR_FILE_NAME
    anchor.unlink()
    paths.append(anchor)
    if is_asset_dir:
        asset = Item(p, repo=repo)
        # TODO: asset['onyo.path.file']
        asset_dir_file = p / OnyoRepo.ASSET_DIR_FILE_NAME
        asset_dir_file.unlink()
        paths.append(asset_dir_file)
    p.rmdir()
    if is_asset_dir:
        asset['onyo.is.directory'] = False  # pyre-ignore[61]  No, this is not "not always defined".
        repo.write_asset_content(asset)  # pyre-ignore[61]
        paths.append(p)  # TODO: Does this need staging? Don't think so, but make sure.
    return paths, []


def mover(src: Path, dst: Path) -> list[Path]:
    r"""helper function for move assets/directories executors"""
    # expected: dst is inventory dir!
    src.rename(dst / src.name)
    return [src, dst / src.name]


def exec_move_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    return mover(operands[0], operands[1]), []


def exec_move_directories(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    return mover(operands[0], operands[1]), []


def renamer(src: Path, dst: Path) -> list[Path]:
    # expected: full path as dst
    src.rename(dst)
    return [src, dst]


def exec_rename_directories(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    return renamer(operands[0], operands[1]), []


def exec_rename_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    return renamer(operands[0], operands[1]), []


def exec_modify_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    # expected: (Asset, Asset)
    new = operands[1]
    repo.write_asset_content(new)
    return [new['onyo.path.absolute']], []


def generic_executor(func: Callable, repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    r"""This is intended for simple FS operations on non-inventory files

    only current usecase is recursive remove_directory. Not yet meant to be a stable implementation
    """
    func(operands)
    return [operands[0]], []
