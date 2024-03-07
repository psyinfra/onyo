import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_mv


@pytest.mark.ui({'yes': True})
def test_onyo_mv_errors(inventory: Inventory) -> None:
    """`onyo_mv` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'
    dir_path2 = inventory.root / 'different' / 'place'

    # move directory into itself
    pytest.raises(OSError,
                  onyo_mv,
                  inventory,
                  source=dir_path,
                  destination=dir_path,
                  message="some subject\n\nAnd a body")

    # move asset into non-existing directory
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=asset_path,
                  destination=dir_path / "doesnotexist",
                  message="some subject\n\nAnd a body")

    # move dir into non-existing directory
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=inventory.root / "somewhere",
                  destination=dir_path / "doesnotexist" / "somewhere",
                  message="some subject\n\nAnd a body")

    # rename asset file
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=asset_path,
                  destination=asset_path.parent / "new_asset_name",
                  message="some subject\n\nAnd a body")

    # target already exists
    inventory.add_directory(asset_path.parent / dir_path.name)
    inventory.commit("add target dir")
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=dir_path,
                  destination=asset_path.parent,
                  message="some subject\n\nAnd a body")

    # source does not exist
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=inventory.root / "not-existent",
                  destination=dir_path,
                  message="some subject\n\nAnd a body")

    # renaming multiple sources at once is not allowed
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=[dir_path, dir_path2],
                  destination=inventory.root / "new_name",
                  message="some subject\n\nAnd a body")

    # no error scenario leaves the inventory unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_errors_before_mv(inventory: Inventory) -> None:
    """`onyo_mv` must raise the correct error and is not allowed to move/commit anything, if one of
    the sources does not exist.
    """
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    destination_path = inventory.root / 'empty'
    old_hexsha = inventory.repo.git.get_hexsha()

    # one of multiple sources does not exist
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=[asset_path, inventory.root / "not-existent"],
                  destination=destination_path,
                  message="some subject\n\nAnd a body")

    # nothing was moved and no new commit was created
    assert asset_path.is_file()
    assert not (destination_path / asset_path.name).is_file()
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.repo_dirs("a/b/c", "a/d/c")
def test_onyo_mv_src_to_dest_with_same_name(inventory: Inventory) -> None:
    """Allow to move a directory into another one with the same name."""
    source_path = inventory.root / "a" / "b" / "c"
    destination_path = inventory.root / "a" / "d" / "c"
    old_hexsha = inventory.repo.git.get_hexsha()

    # move a source dir into a destination dir with the same name
    onyo_mv(inventory,
            source=source_path,
            destination=destination_path,
            message="some subject\n\nAnd a body")

    # source
    assert not source_path.exists()
    assert (source_path / OnyoRepo.ANCHOR_FILE_NAME) not in inventory.repo.git.files
    # directory was moved
    assert (destination_path / source_path.name).is_dir()
    assert (destination_path / source_path.name / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert inventory.repo.is_inventory_dir(destination_path / source_path.name)
    assert (destination_path / source_path.name / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_move_simple(inventory: Inventory) -> None:
    """Move an asset and a directory in one commit into a destination."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'
    destination_path = inventory.root / 'different' / 'place'
    old_hexsha = inventory.repo.git.get_hexsha()

    # move an asset and a dir to the same destination
    onyo_mv(inventory,
            source=[asset_path, dir_path],
            destination=destination_path,
            message="some subject\n\nAnd a body")

    # asset was moved
    assert inventory.repo.is_asset_path(destination_path / asset_path.name)
    assert (destination_path / asset_path.name) in inventory.repo.git.files
    assert not asset_path.exists()
    assert asset_path not in inventory.repo.git.files
    # dir was moved
    assert inventory.repo.is_inventory_dir(destination_path / dir_path.name)
    assert (destination_path / dir_path.name / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    assert not dir_path.exists()
    assert (destination_path / dir_path.name / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_move_to_explicit_destination(inventory: Inventory) -> None:
    """Allow moving a source to a destination stating the
    destination name explicitely, e.g.:
    inventory.root/dir1/asset -> inventory.root/dir2/asset.
    """
    dir_path = inventory.root / 'somewhere' / 'nested'
    # move by explicitly restating the source's name:
    src = dir_path
    destination_path = inventory.root / src.name
    old_hexsha = inventory.repo.git.get_hexsha()

    onyo_mv(inventory,
            source=src,
            destination=destination_path,
            message="some subject\n\nAnd a body")

    # source is moved
    assert (src / OnyoRepo.ANCHOR_FILE_NAME) not in inventory.repo.git.files
    assert not src.exists()
    # destination is correct
    assert inventory.repo.is_inventory_dir(destination_path)
    assert (destination_path / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    assert (destination_path / OnyoRepo.ANCHOR_FILE_NAME).is_file()
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_rename_directory(inventory: Inventory) -> None:
    """`onyo_mv` must allow renaming of a directory."""
    dir_path = inventory.root / 'somewhere' / 'nested'
    destination_path = dir_path.parent / 'newname'
    old_hexsha = inventory.repo.git.get_hexsha()

    onyo_mv(inventory,
            source=dir_path,
            destination=destination_path,
            message="some subject\n\nAnd a body")

    # source
    assert not dir_path.exists()
    assert (dir_path / OnyoRepo.ANCHOR_FILE_NAME) not in inventory.repo.git.files
    assert not inventory.repo.is_inventory_dir(dir_path)
    # destination is correct
    assert destination_path.is_dir()
    assert (destination_path / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    assert inventory.repo.is_inventory_dir(destination_path)
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_and_rename(inventory: Inventory) -> None:
    old_hexsha = inventory.repo.git.get_hexsha()
    source = inventory.root / "somewhere"
    destination = inventory.root / 'empty' / "newname"
    # rename and move of a directory in one call
    onyo_mv(inventory,
            source=source,
            destination=destination,
            message="some subject\n\nAnd a body")
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
    assert not inventory.repo.is_inventory_dir(source)
    assert inventory.repo.is_inventory_dir(destination)
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_into_asset(inventory: Inventory) -> None:
    asset = dict(some_key="some_value",
                 type="TYPE",
                 make="MAKE",
                 model="MODEL",
                 serial="SERIAL2",
                 other=1,
                 directory=inventory.root)
    asset_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL2"
    inventory.add_asset(asset)
    inventory.commit("Add second asset")

    old_hexsha = inventory.repo.git.get_hexsha()
    source = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    onyo_mv(inventory,
            source=source,
            destination=asset_path,
            message="Move asset into asset to create asset dir")
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
    assert not source.exists()
    # Turned destination into asset dir:
    assert inventory.repo.is_asset_dir(asset_path)
    # Actually moved source into destination:
    assert inventory.repo.is_asset_path(asset_path / "TYPE_MAKER_MODEL.SERIAL")
