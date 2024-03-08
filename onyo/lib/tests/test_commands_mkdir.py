import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_mkdir
from ..exceptions import NoopError


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_errors(inventory: Inventory) -> None:
    """`onyo_mkdir` must raise the correct error in different illegal or impossible calls."""
    dir_path = inventory.root / 'empty'

    # mkdir on existing directory path
    pytest.raises(NoopError,
                  onyo_mkdir,
                  inventory,
                  dirs=[dir_path],
                  message="some subject\n\nAnd a body")

    # mkdir outside the repository
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[(inventory.root / ".." / "outside").resolve()],
                  message="some subject\n\nAnd a body")

    # mkdir with empty list
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[],
                  message="some subject\n\nAnd a body")

    # mkdir on illegal but non-existing name ".anchor"
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[inventory.root / "subdir" / ".anchor"],
                  message="some subject\n\nAnd a body")

    # mkdir on illegal but non-existing directory in .git/
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[inventory.root / ".git" / "new-dir"],
                  message="some subject\n\nAnd a body")

    # mkdir is not allowed to create a new .git/ in a subdirectory
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[dir_path / ".git"],
                  message="some subject\n\nAnd a body")

    # mkdir on illegal but non-existing directory in .onyo/
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[inventory.root / ".onyo" / "new-dir"],
                  message="some subject\n\nAnd a body")

    # mkdir is not allowed to create a new .onyo/ in a subdirectory
    pytest.raises(ValueError,
                  onyo_mkdir,
                  inventory,
                  dirs=[dir_path / ".onyo"],
                  message="some subject\n\nAnd a body")

    # no error scenario leaves the inventory unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_errors_before_mkdir(inventory: Inventory) -> None:
    """`onyo_mkdir` must raise the correct error and is not allowed to create/commit anything, if
    one of the specified paths is not valid.
    """
    dir_path_new = inventory.root / 'new_dir'
    dir_path_existing = inventory.root / 'empty'
    old_hexsha = inventory.repo.git.get_hexsha()

    # one of multiple sources does already exist
    pytest.raises(NoopError,
                  onyo_mkdir,
                  inventory,
                  dirs=[dir_path_new,
                        dir_path_existing],
                  message="some subject\n\nAnd a body")

    # no new directory/anchor was created
    assert not dir_path_new.is_dir()
    assert not (dir_path_new / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert not (dir_path_new / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_simple(inventory: Inventory) -> None:
    """Create a single new directory."""
    dir_path_new = inventory.root / 'new_dir'
    old_hexsha = inventory.repo.git.get_hexsha()

    # create a new directory
    onyo_mkdir(inventory,
               dirs=[dir_path_new],
               message="some subject\n\nAnd a body")

    # directory was created and anchor exists
    assert dir_path_new.is_dir()
    assert inventory.repo.is_inventory_dir(dir_path_new)
    assert (dir_path_new / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_path_new / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_multiple(inventory: Inventory) -> None:
    """Create multiple new directories in a single call and with one commit."""
    dir_path_new1 = inventory.root / 'new_dir1'
    dir_path_new2 = inventory.root / 'new_dir2'
    dir_path_new3 = inventory.root / 'new_dir3'
    old_hexsha = inventory.repo.git.get_hexsha()

    # create a new directory
    onyo_mkdir(inventory,
               dirs=[dir_path_new1,
                     dir_path_new2,
                     dir_path_new3],
               message="some subject\n\nAnd a body")

    # directories were created and anchor exists for 1.
    assert dir_path_new1.is_dir()
    assert inventory.repo.is_inventory_dir(dir_path_new1)
    assert (dir_path_new1 / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_path_new1 / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # directories were created and anchor exists for 2.
    assert dir_path_new2.is_dir()
    assert inventory.repo.is_inventory_dir(dir_path_new2)
    assert (dir_path_new2 / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_path_new2 / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # directories were created and anchor exists for 3.
    assert dir_path_new3.is_dir()
    assert inventory.repo.is_inventory_dir(dir_path_new3)
    assert (dir_path_new3 / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_path_new3 / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_create_multiple_subdirectories(inventory: Inventory) -> None:
    """Create multiple not-yet-existing subdirectories at once."""
    dir_x = inventory.root / 'x'
    dir_y = inventory.root / 'x' / 'y'
    dir_z = inventory.root / 'x' / 'y' / 'z'

    old_hexsha = inventory.repo.git.get_hexsha()

    # call onyo_mkdir with the deepest new directory, and create the other dirs implicitely
    onyo_mkdir(inventory,
               dirs=[dir_z],
               message="some subject\n\nAnd a body")

    # directory x was created and anchor exists
    assert dir_x.is_dir()
    assert inventory.repo.is_inventory_dir(dir_x)
    assert (dir_x / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_x / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # directory x was created and anchor exists
    assert dir_y.is_dir()
    assert inventory.repo.is_inventory_dir(dir_y)
    assert (dir_y / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_y / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # directory x was created and anchor exists
    assert dir_z.is_dir()
    assert inventory.repo.is_inventory_dir(dir_z)
    assert (dir_z / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_z / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_allows_duplicates(inventory: Inventory) -> None:
    """Calling `onyo_mkdir()` with a list containing the same path multiple times does not error."""
    dir_path_new = inventory.root / 'new_dir'
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_mkdir()` with `dirs` containing duplicates
    onyo_mkdir(inventory,
               dirs=[dir_path_new, dir_path_new, dir_path_new],
               message="some subject\n\nAnd a body")

    # the new directory was created and anchor exists
    assert dir_path_new.is_dir()
    assert inventory.repo.is_inventory_dir(dir_path_new)
    assert (dir_path_new / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert (dir_path_new / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mkdir_asset(inventory: Inventory) -> None:
    """`onyo_mkdir` turns an existing asset into an asset dir."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    onyo_mkdir(inventory,
               dirs=[asset_path],
               message="some subject\n\nAnd a body")

    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.is_inventory_dir(asset_path)

    # re-execution fails:
    with pytest.raises(NoopError, match="already is a directory"):
        onyo_mkdir(inventory,
                   dirs=[asset_path],
                   message="some subject\n\nAnd a body")
