from pathlib import Path

import pytest

from onyo.lib.exceptions import InvalidAssetError
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_cat


@pytest.mark.ui({'yes': True})
def test_onyo_cat_errors(inventory: Inventory) -> None:
    r"""`onyo_cat` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'

    # cat with no file
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[])

    # cat on dir
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[dir_path])

    # cat on non-existing file
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[dir_path / "does_not_exi.st"])

    # cat on untracked file
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[inventory.root / "untracked" / "file"])

    # cat on path outside onyo repository
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[inventory.root / ".."])

    # one of multiple is non-existing
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[asset_path,
                         inventory.root / "doesnotexist",
                         asset_path])

    # cat on .anchor
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[dir_path / OnyoRepo.ANCHOR_FILE_NAME])

    # cat on a template file
    pytest.raises(ValueError,
                  onyo_cat,
                  inventory,
                  paths=[inventory.repo.dot_onyo / "templates" / "laptop.example"])

    # cat on a file that is in the inventory, but has invalid YAML contents
    invalid_path = inventory.root / "in_va_l.id"
    invalid_path.touch()
    invalid_path.write_text("key: value\ninvalid")
    inventory.repo.git._git(["add", str(invalid_path)])
    inventory.commit("Invalid file added")
    pytest.raises(InvalidAssetError,
                  onyo_cat,
                  inventory,
                  paths=[invalid_path])


@pytest.mark.ui({'yes': True})
def test_onyo_cat_single(inventory: Inventory,
                         capsys) -> None:
    r"""`onyo_cat()` a single valid asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # cat single asset
    onyo_cat(inventory,
             paths=[asset_path])

    # verify asset contents are in output
    assert Path.read_text(asset_path) in capsys.readouterr().out


@pytest.mark.ui({'yes': True})
def test_onyo_cat_multiple(inventory: Inventory,
                           capsys) -> None:
    r"""`onyo_cat()` on multiple valid assets."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    # TODO: simplify with new fixtures
    # add a different second asset to the inventory
    inventory.add_asset(dict(some_key="some_value",
                             type="TYPE",
                             make="MAKER",
                             model=dict(name="MODEL"),
                             serial="SERIAL2",
                             other=1,
                             directory=inventory.root)
                        )
    asset_path2 = inventory.root / "TYPE_MAKER_MODEL.SERIAL2"
    inventory.commit("Second asset added")

    # cat multiple assets at once
    onyo_cat(inventory,
             paths=[asset_path1,
                    asset_path2])

    # verify the output contains both assets
    out = capsys.readouterr().out
    assert Path.read_text(asset_path1) in out
    assert Path.read_text(asset_path2) in out


@pytest.mark.ui({'yes': True})
def test_onyo_cat_with_duplicate_path(inventory: Inventory,
                                      capsys) -> None:
    r"""`onyo_cat()` Multiple times on the same asset succeeds."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # cat single asset
    onyo_cat(inventory,
             paths=[asset_path, asset_path, asset_path])

    # verify output contains the asset contents once for each time the asset is in `paths`
    assert capsys.readouterr().out.count(Path.read_text(asset_path)) == 3


def test_onyo_cat_asset_dir(inventory: Inventory,
                            capsys) -> None:
    inventory.add_asset(dict(some_key="some_value",
                             type="TYPE",
                             make="MAKER",
                             model=dict(name="MODEL"),
                             serial="SERIAL2",
                             other=1,
                             directory=inventory.root,
                             is_asset_directory=True)
                        )
    asset_dir = inventory.root / "TYPE_MAKER_MODEL.SERIAL2"
    inventory.commit("add an asset dir")

    assert inventory.repo.is_asset_dir(asset_dir)
    onyo_cat(inventory, [asset_dir])
    assert "some_key: some_value" in capsys.readouterr().out
