import pytest

from onyo.lib.exceptions import InvalidInventoryOperation
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_mv


@pytest.mark.ui({'yes': True})
def test_onyo_mv_into_self(inventory: Inventory) -> None:
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'

    # move into itself:
    pytest.raises(InvalidInventoryOperation,
                  onyo_mv,
                  inventory,
                  source=dir_path,
                  destination=dir_path,
                  message="some subject\n\nAnd a body")

    # move asset into non-existing
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=asset_path,
                  destination=dir_path / "doesnotexist",
                  message="some subject\n\nAnd a body")

    # move dir into non-existing
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=inventory.root / "somewhere",
                  destination=dir_path / "doesnotexist" / "somewhere",
                  message="some subject\n\nAnd a body")

    # rename including a move
    pytest.raises(InvalidInventoryOperation,
                  onyo_mv,
                  inventory,
                  source=inventory.root / "somewhere",
                  destination=dir_path / "newname",
                  message="some subject\n\nAnd a body")

    # move to existing file
    pytest.raises(ValueError,
                  onyo_mv,
                  inventory,
                  source=dir_path,
                  destination=asset_path,
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


@pytest.mark.ui({'yes': True})
def test_onyo_mv_move_simple(inventory: Inventory) -> None:
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'
    destination_path = inventory.root / 'different' / 'place'

    # move an asset and a dir to the same destination
    onyo_mv(inventory,
            source=[asset_path, dir_path],
            destination=destination_path,
            message="some subject\n\nAnd a body")

    # asset was moved
    assert inventory.repo.is_asset_path(destination_path / asset_path.name)
    assert (destination_path / asset_path.name) in inventory.repo.git.files
    assert not asset_path.exists()
    # dir was moved
    assert inventory.repo.is_inventory_dir(destination_path / dir_path.name)
    assert (destination_path / dir_path.name / OnyoRepo.ANCHOR_FILE).is_file()
    assert (destination_path / dir_path.name / OnyoRepo.ANCHOR_FILE) in inventory.repo.git.files
    assert not dir_path.exists()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_move_explicit(inventory: Inventory) -> None:
    dir_path = inventory.root / 'somewhere' / 'nested'
    # move by explicitly restating the source's name:
    src = dir_path
    # `dst` does not yet exist, which would indicate a renaming if it wasn't the same name as the source.
    # If recognized as a renaming, however, it should fail because not only the name but also the parent changed, which
    # implies two operations: A move and a renaming (with no order given).
    dst = inventory.root / src.name
    onyo_mv(inventory,
            source=src,
            destination=dst,
            message="some subject\n\nAnd a body")

    assert inventory.repo.is_inventory_dir(dst)
    assert (dst / OnyoRepo.ANCHOR_FILE) in inventory.repo.git.files
    assert not src.exists()


@pytest.mark.ui({'yes': True})
def test_onyo_mv_rename(inventory: Inventory) -> None:
    dir_path = inventory.root / 'somewhere' / 'nested'
    new_name = dir_path.parent / 'newname'

    onyo_mv(inventory,
            source=dir_path,
            destination=new_name,
            message="some subject\n\nAnd a body")

    assert inventory.repo.is_inventory_dir(new_name)
    assert (new_name / OnyoRepo.ANCHOR_FILE) in inventory.repo.git.files
    assert not dir_path.exists()
