from pathlib import Path
from typing import Callable

from onyo.lib.onyo import OnyoRepo


# Executors signature: (repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]
#                      first returned list are the paths that need to be committed
#                      second list are the paths that need to be staged (not previously tracked)

# Attention! No input validation in executors -> document "not intended for direct use"
# Those callables are to be registered with operators. Operations have to make sure to deliver
# valid objects. We don't want to issue a ton of stat calls just to validate the same paths
# throughout every layer of onyo over and over.


def exec_new_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    """Executor for the 'new_asset' operation

    Parameters
    ----------
    repo: OnyoRepo
      Onyo repository to operate on
    operands: list
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
    path = asset.get('path')
    return [path], [path]


def exec_new_directories(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    """Executor for the 'new_directory' operation
    """
    paths = repo.mk_inventory_dirs(operands[0])
    return paths, paths


def exec_remove_assets(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    p = operands[0] if isinstance(operands[0], Path) else operands[0].get('path')
    paths = []
    if p.is_dir():
        paths.append(p / OnyoRepo.ANCHOR_FILE)
        # we were told p is an asset. It's also a dir, ergo an asset dir
        paths.append(p / OnyoRepo.ASSET_DIR_FILE)
    else:
        paths = [p]
    for p in paths:
        # missing_ok=True, b/c several operations may want to remove the same thing. No reason to fail here.
        p.unlink(missing_ok=True)
    return paths, []


def exec_remove_directories(repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    paths = []
    p = operands[0]
    is_asset_dir = repo.is_asset_dir(p)  # required after dir was removed, therefore store
    asset = dict()
    anchor = p / repo.ANCHOR_FILE
    anchor.unlink()
    paths.append(anchor)
    if is_asset_dir:
        asset = repo.get_asset_content(p)
        asset_dir_file = p / repo.ASSET_DIR_FILE
        asset_dir_file.unlink()
        paths.append(asset_dir_file)
    p.rmdir()
    if is_asset_dir:
        asset['is_asset_directory'] = False
        repo.write_asset_content(asset)
        paths.append(p)  # TODO: Does this need staging? Don't think so, but make sure.
    return paths, []


def mover(src: Path, dst: Path) -> list[Path]:
    """helper function for move assets/directories executors"""
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
    return [new['path']], []


def generic_executor(func: Callable, repo: OnyoRepo, operands: tuple) -> tuple[list[Path], list[Path]]:
    """This is intended for simple FS operations on non-inventory files

    only current usecase is recursive remove_directory. Not yet meant to be a stable implementation"""
    func(operands)
    return [operands[0]], []
