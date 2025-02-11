from __future__ import annotations

import pytest

from onyo.lib.commands import (
    onyo_mkdir,
    onyo_rmdir,
)
from onyo.lib.consts import ANCHOR_FILE_NAME
from onyo.lib.exceptions import (
    InventoryDirNotEmpty,
    InvalidInventoryOperationError,
    NoopError,
)
from onyo.lib.inventory import Inventory
from . import check_commit_msg


@pytest.mark.ui({'yes': True})
def test_onyo_rmdir_errors(inventory: Inventory) -> None:
    r"""Raise the correct error in different illegal or impossible calls."""

    asset_file = inventory.root / 'somewhere/nested/TYPE_MAKER_MODEL.SERIAL'
    dir_not_empty = inventory.root / 'somewhere'

    # rmdir on existing asset file
    pytest.raises(NoopError,
                  onyo_rmdir,
                  inventory,
                  dirs=[asset_file])

    # rmdir on non-empty directory
    pytest.raises(InventoryDirNotEmpty,
                  onyo_rmdir,
                  inventory,
                  dirs=[dir_not_empty])

    # rmdir outside the repository
    pytest.raises(InvalidInventoryOperationError,
                  onyo_rmdir,
                  inventory,
                  dirs=[(inventory.root / ".." / "outside").resolve()])

    # rmdir with empty list
    pytest.raises(NoopError,
                  onyo_rmdir,
                  inventory,
                  dirs=[])

    # rmdir an empty dir that is under .git/
    empty_under_git = inventory.root / ".git" / "empty"
    empty_under_git.mkdir()
    pytest.raises(InvalidInventoryOperationError,
                  onyo_rmdir,
                  inventory,
                  dirs=[empty_under_git])

    # rmdir an empty dir that is under .onyo/
    empty_under_onyo = inventory.root / ".onyo" / "empty"
    empty_under_onyo.mkdir()
    pytest.raises(InvalidInventoryOperationError,
                  onyo_rmdir,
                  inventory,
                  dirs=[empty_under_onyo])

    # no error scenario leaves the inventory unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_rmdir_errors_before_rmdir(inventory: Inventory) -> None:
    r"""Raise and don't remove/commit anything, if one of the specified paths is not valid."""

    old_hexsha = inventory.repo.git.get_hexsha()

    dir_empty = inventory.root / 'empty'
    dir_not_empty = inventory.root / 'somewhere'
    asset_file = inventory.root / 'somewhere/nested/TYPE_MAKER_MODEL.SERIAL'

    # one of multiple targets is not empty
    pytest.raises(InvalidInventoryOperationError,
                  onyo_rmdir,
                  inventory,
                  dirs=[dir_empty,
                        dir_not_empty,
                        asset_file])

    # targets were untouched
    assert dir_empty.is_dir()
    assert (dir_empty / ANCHOR_FILE_NAME).is_file()
    assert (dir_empty / ANCHOR_FILE_NAME) in inventory.repo.git.files  # noqa: E713
    assert dir_not_empty.is_dir()
    assert (dir_not_empty / ANCHOR_FILE_NAME).is_file()
    assert (dir_not_empty / ANCHOR_FILE_NAME) in inventory.repo.git.files  # noqa: E713
    assert asset_file.is_file()
    assert asset_file in inventory.repo.git.files  # noqa: E713

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.parametrize('message', ["", None, "message with spe\"cial\\char\'acteஞrs"])
@pytest.mark.parametrize('auto_message', [True, False])
def test_onyo_rmdir_simple(inventory: Inventory,
                           message,
                           auto_message) -> None:
    r"""Remove a single directory."""

    dir_path_empty = inventory.root / 'empty'
    old_hexsha = inventory.repo.git.get_hexsha()

    # remove a directory
    onyo_rmdir(inventory,
               dirs=[dir_path_empty],
               message=message,
               auto_message=auto_message)

    # directory was deleted
    assert not (dir_path_empty / ANCHOR_FILE_NAME).is_file()
    assert (dir_path_empty / ANCHOR_FILE_NAME) not in inventory.repo.git.files
    assert not dir_path_empty.is_dir()
    assert not inventory.repo.is_inventory_dir(dir_path_empty)

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
    check_commit_msg(inventory, message, auto_message, "rmdir [")


@pytest.mark.ui({'yes': True})
def test_onyo_rmdir_multiple(inventory: Inventory) -> None:
    r"""Remove multiple directories in a single call and with one commit."""

    empty_dirs = [
        inventory.root / 'empty_dir1',
        inventory.root / 'empty_dir2',
        inventory.root / 'empty_dir3',
    ]

    # create the directories
    onyo_mkdir(inventory,
               dirs=[*empty_dirs])

    # quick sanity check
    for d in empty_dirs:
        assert inventory.repo.is_inventory_dir(d)

    # get the commit
    old_hexsha = inventory.repo.git.get_hexsha()

    # remove the directories
    onyo_rmdir(inventory,
               dirs=[*empty_dirs])

    # directories were deleted
    for d in empty_dirs:
        assert not (d / ANCHOR_FILE_NAME).is_file()
        assert (d / ANCHOR_FILE_NAME) not in inventory.repo.git.files
        assert not d.is_dir()
        assert not inventory.repo.is_inventory_dir(d)

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_rmdir_allows_duplicates(inventory: Inventory) -> None:
    r"""Do not error when the same path is passed multiple times."""

    dir_path_empty = inventory.root / 'empty'
    old_hexsha = inventory.repo.git.get_hexsha()

    # remove the same single directory multiple times
    onyo_rmdir(inventory,
               dirs=[dir_path_empty, dir_path_empty, dir_path_empty])

    # directory was deleted
    assert not (dir_path_empty / ANCHOR_FILE_NAME).is_file()
    assert (dir_path_empty / ANCHOR_FILE_NAME) not in inventory.repo.git.files
    assert not dir_path_empty.is_dir()
    assert not inventory.repo.is_inventory_dir(dir_path_empty)

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_rmdir_asset(inventory: Inventory) -> None:
    r"""Convert an Asset Directory into an Asset File."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # convert to an asset directory
    onyo_mkdir(inventory,
               dirs=[asset_path])

    # quick sanity check
    assert inventory.repo.is_inventory_dir(asset_path)

    # get the commit
    old_hexsha = inventory.repo.git.get_hexsha()

    # convert the asset directory back to an asset file
    onyo_rmdir(inventory,
               dirs=[asset_path])

    assert not inventory.repo.is_inventory_dir(asset_path)
    assert asset_path.is_file()
    assert asset_path in inventory.repo.git.files

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()

    # re-execution fails
    with pytest.raises(NoopError, match="is already an Asset File"):
        onyo_rmdir(inventory,
                   dirs=[asset_path])
