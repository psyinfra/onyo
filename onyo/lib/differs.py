from __future__ import annotations

from difflib import unified_diff
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.utils import dict_to_asset_yaml

if TYPE_CHECKING:
    from typing import Generator

# Differs signature: (repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
# yielded strings are supposed to be lines of a diff for a given operation

# TODO: Double-check we always report posix paths!


def diff_assets(asset_old: dict, asset_new: dict) -> Generator[str, None, None]:
    yield from unified_diff(dict_to_asset_yaml(asset_old).splitlines(keepends=False),
                            dict_to_asset_yaml(asset_new).splitlines(keepends=False),
                            fromfile=str(asset_old.get('onyo.path.absolute', '')),
                            tofile=str(asset_new.get('onyo.path.absolute', '')),
                            lineterm="")


def diff_path_change(src: Path, dst: Path) -> Generator[str, None, None]:
    yield f"{str(src)} -> {str(dst)}"


diff_new_asset = partial(diff_assets, asset_old={})
diff_rm_asset = partial(diff_assets, asset_new={})
diff_modified_asset = diff_assets
diff_renamed_asset = diff_assets  # This is the same, because a rename requires a change in keys composing the name (or change in config).


def diff_moved_asset(asset_old: dict | Path, asset_new: Path) -> Generator[str, None, None]:
    # could be same. Just check isinstance?
    yield from diff_path_change(asset_old if isinstance(asset_old, Path) else asset_old.get('onyo.path.absolute'),
                                asset_new)


def differ_new_assets(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield from diff_assets(asset_old={}, asset_new=operands[0])


def differ_new_directories(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield f"+{str(operands[0])}"


def differ_remove_assets(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield f"-{str(operands[0]) if isinstance(operands[0], Path) else operands[0].get('onyo.path.absolute')}"


def differ_remove_directories(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield f"-{str(operands[0])}"


def differ_move_assets(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield from diff_path_change(operands[0], operands[1])


def differ_move_directories(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield from diff_path_change(operands[0], operands[1])


def differ_rename_directories(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield from diff_path_change(operands[0], operands[1])


def differ_modify_assets(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield from diff_assets(operands[0], operands[1])


def differ_rename_assets(repo: OnyoRepo, operands: tuple) -> Generator[str, None, None]:
    yield from diff_path_change(operands[0], operands[1])
