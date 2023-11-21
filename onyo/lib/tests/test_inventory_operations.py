import pytest

from onyo.lib.assets import Asset
from onyo.lib.consts import RESERVED_KEYS, PSEUDO_KEYS
from onyo.lib.exceptions import InvalidInventoryOperation, NoopError, NotAnAssetError
from onyo.lib.inventory import Inventory, OPERATIONS_MAPPING
from onyo.lib.onyo import OnyoRepo


# TODO: - Inventory fixture(s)
#       - mocks


# TODO: Parameterize tests? run a method with different paths/objects(Asset); especially asset/dir vs asset dir
#       wherever the outcome should be identical (like move)

# TODO: Should an asset dir be able to contain a plain dir? Think so.


def num_operations(inventory: Inventory, name: str) -> int:
    """Helper to get number of registered operations in `inventory` of type `name`."""
    return len([op for op in inventory.operations if op.operator is OPERATIONS_MAPPING[name]])


def test_Inventory_instantiation(repo: OnyoRepo) -> None:

    inventory = Inventory(repo)
    # operations registry is initialized:
    assert inventory.operations == []


def test_add_asset(repo: OnyoRepo) -> None:
    # TODO: mock repo? Real one not needed here.
    #       Possibly also mock add_directory instead.

    # TODO: check validation? (not yet integrated)

    inventory = Inventory(repo)

    newdir1 = inventory.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_file = newdir2 / "test_I_mk1.123"
    asset = Asset(some_key="some_value",
                  other=1,
                  directory=newdir2,
                  type="test",
                  make="I",
                  model="mk1",
                  serial="123"
                  )
    assert num_operations(inventory, 'new_assets') == 0
    assert num_operations(inventory, 'new_directories') == 0

    inventory.add_asset(asset)

    # operations to add new asset and two dirs are registered:
    assert num_operations(inventory, 'new_assets') == 1
    assert num_operations(inventory, 'new_directories') == 2
    operands = [op.operands for op in inventory.operations]
    assert all(isinstance(o, tuple) for o in operands)
    assert (asset,) in operands
    assert (newdir1,) in operands
    assert (newdir2,) in operands

    # nothing done on disc yet:
    assert not asset_file.exists()
    assert not newdir2.exists()
    assert not newdir1.exists()

    # TODO: test diff

    # now commit:
    inventory.commit("Add a new asset")
    assert repo.is_inventory_dir(newdir1)
    assert repo.is_inventory_dir(newdir2)
    assert repo.is_asset_path(asset_file)
    asset_from_disc = repo.get_asset_content(asset_file)
    assert asset_file == asset_from_disc.pop('path')
    assert asset_from_disc == {k: v for k, v in asset.items() if k not in RESERVED_KEYS + PSEUDO_KEYS}
    # TODO: check commit message

    # required keys must not be empty
    asset.update(dict(model=""))
    pytest.raises(ValueError, inventory.add_asset, asset)

    # To be added Asset requires a path:
    asset = Asset(a_key='a_value')
    pytest.raises(ValueError, inventory.add_asset, asset)

    # Asset must not yet exist:  (TODO: This may be wrong. Seems better if it must not yet exist as an asset,
    #                                   but may exist as an untracked file! Note, that this is not testing a command,
    #                                   but an inventory operation.)
    existing_asset_file = repo.git.root / 'root_asset'
    existing_asset_file.touch()
    asset = Asset(some='whatever', path=existing_asset_file)
    pytest.raises(ValueError, inventory.add_asset, asset)

    # TODO: should also fail when adding an asset that is already pending? Or one that is also being removed, etc?


def test_remove_asset(inventory: Inventory) -> None:

    # NOTE: First trial using inventory fixture

    doesnotexist = inventory.root / "root_asset"
    pytest.raises(NotAnAssetError, inventory.remove_asset, doesnotexist)

    isadir = inventory.root / "a_dir"
    isadir.mkdir()
    pytest.raises(NotAnAssetError, inventory.remove_asset, isadir)

    # TODO: Can't remove untracked?? See similar cases in new_asset, new_dir

    # TODO: We should get such paths from the fixture! Otherwise it doesn't make things easier.
    asset_file = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    assert asset_file.exists()

    asset = inventory.get_asset(asset_file)
    inventory.remove_asset(asset)
    # operation registered:
    assert num_operations(inventory, 'remove_assets') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert asset in inventory.operations[0].operands

    # Still on disc:
    assert asset_file.exists()

    # TODO: test diff

    # now commit:
    inventory.commit("Remove an asset")
    # asset file is removed (but not the containing dir):
    assert not asset_file.exists()
    assert asset_file.parent.is_dir()
    # path does not qualify as an asset path anymore:
    assert not inventory.repo.is_asset_path(asset_file)
    # but parent dir still is an inventory dir:
    assert inventory.repo.is_inventory_dir(asset_file.parent)


def test_move_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_file = newdir2 / "test_I_mk1.123"
    asset = Asset(some_key="some_value",
                  other=1,
                  directory=newdir2,
                  type="test",
                  make="I",
                  model="mk1",
                  serial="123"
                  )
    inventory.add_asset(asset)
    inventory.commit("First asset added")

    # non-existing destination raises:
    pytest.raises(ValueError, inventory.move_asset, asset, newdir1 / "doesnotexist")

    # move to same place:
    pytest.raises(ValueError, inventory.move_asset, asset, newdir2)

    # valid target:
    inventory.move_asset(asset, newdir1)
    assert num_operations(inventory, 'move_assets') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert asset_file in inventory.operations[0].operands
    assert newdir1 in inventory.operations[0].operands

    # nothing done on disc yet:
    assert asset_file.is_file()
    assert not (newdir1 / asset_file.name).exists()

    # TODO: test diff

    # now commit:
    inventory.commit("Move an asset")
    assert not asset_file.exists()
    assert (newdir1 / asset_file.name).is_file()


def test_rename_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset = Asset(some_key="some_value",
                  type="TYPE",
                  make="MAKER",
                  model="MODEL",
                  serial="SERIAL",
                  other=1,
                  directory=newdir2
                  )
    inventory.add_asset(asset)
    inventory.commit("First asset added")

    # invalid name according to default config:
    pytest.raises(ValueError, inventory.rename_asset, asset, "new_name")

    # rename to itself raises:
    pytest.raises(NoopError, inventory.rename_asset, asset, "TYPE_MAKER_MODEL.SERIAL")

    # Note: No commit here. Valid rename only via modify ATM. Hence, tested in modify asset instead.
    # Alternative: Modify file directly instead and rename here?


def test_modify_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_file = newdir2 / "TYPE_MAKER_MODEL.SERIAL"
    asset = Asset(some_key="some_value",
                  type="TYPE",
                  make="MAKER",
                  model="MODEL",
                  serial="SERIAL",
                  other=1,
                  directory=newdir2
                  )
    inventory.add_asset(asset)
    inventory.commit("First asset added")

    asset_changes = Asset(some_key="new_value",  # arbitrary content change
                          model=""  # empty required key
                          )
    new_asset = asset.copy()
    new_asset.update(asset_changes)

    # required keys must not be empty
    pytest.raises(ValueError, inventory.add_asset, asset)

    new_asset.update(dict(model="CORRECTED-MODEL"))  # implies rename w/ default name config

    # illegal to define 'path' in `new_asset`:
    pytest.raises(ValueError, inventory.modify_asset, asset, new_asset)
    new_asset.pop('path')
    # raises on non-existing asset
    pytest.raises(ValueError, inventory.modify_asset, repo.git.root / "doesnotexist", new_asset)
    # raises on non-asset
    pytest.raises(ValueError, inventory.modify_asset, newdir1, new_asset)

    inventory.modify_asset(asset, new_asset)
    # modify operation:
    assert num_operations(inventory, 'modify_assets') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert asset in inventory.operations[0].operands
    new_asset_file = newdir2 / "TYPE_MAKER_CORRECTED-MODEL.SERIAL"
    assert new_asset in inventory.operations[0].operands
    # implicit rename operation:
    assert num_operations(inventory, 'rename_assets') == 1
    assert isinstance(inventory.operations[1].operands, tuple)
    assert asset_file in inventory.operations[1].operands
    assert new_asset_file in inventory.operations[1].operands

    # nothing done on disc yet:
    assert asset_file.is_file()
    assert not new_asset_file.exists()
    asset_on_disc = repo.get_asset_content(asset_file)
    assert asset_file == asset_on_disc.pop('path')
    assert asset_on_disc == {k: v for k, v in asset.items() if k not in RESERVED_KEYS + PSEUDO_KEYS}

    # TODO: diff

    # now commit:
    inventory.commit("Modify an asset")
    assert not asset_file.exists()
    assert repo.is_asset_path(new_asset_file)
    expected_asset = {k: v for k, v in new_asset.items() if k not in RESERVED_KEYS}
    expected_asset['path'] = new_asset_file
    assert repo.get_asset_content(new_asset_file) == expected_asset


def test_add_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)

    # can not add non-inventory paths:
    invalid_inventory_dir = repo.git.root / '.git' / 'new'
    pytest.raises(ValueError, inventory.add_directory, invalid_inventory_dir)

    # can not add existing dirs:  (TODO: Same as new_asset - this behavior is not entirely correct at this level.
    #                                    dir w/o anchor could get one. Could also be untracked and now to be added.
    existing_inventory_dir = repo.git.root / 'exists'
    existing_inventory_dir.mkdir()
    pytest.raises(ValueError, inventory.add_directory, existing_inventory_dir)

    new_dir = repo.git.root / 'newdir'
    inventory.add_directory(new_dir)

    # operation is registered:
    assert num_operations(inventory, 'new_directories') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert new_dir in inventory.operations[0].operands

    # nothing done on disc yet:
    assert not new_dir.exists()

    # TODO: diff

    # now commit
    inventory.commit("Add new directory")
    assert repo.is_inventory_dir(new_dir)
    assert (new_dir / repo.ANCHOR_FILE).is_file()


def test_remove_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    emptydir = newdir1 / "empty"
    asset_file = newdir2 / "asset_file"
    asset = Asset(some_key="some_value",
                  type="TYPE",
                  make="MAKER",
                  model="MODEL",
                  serial="SERIAL",
                  other=1,
                  directory=newdir2
                  )
    inventory.add_asset(asset)
    inventory.add_directory(emptydir)
    inventory.commit("First asset added")

    # raise on non-dir
    pytest.raises(InvalidInventoryOperation, inventory.remove_directory, asset_file)

    inventory.remove_directory(emptydir)
    assert num_operations(inventory, 'remove_directories') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert emptydir in inventory.operations[0].operands

    # nothing done on disc yet:
    assert emptydir.is_dir()

    # TODO: diff

    # now commit
    inventory.commit("Remove directory")
    assert not emptydir.exists()

    # recursive
    inventory.remove_directory(newdir1)
    assert num_operations(inventory, 'remove_directories') == 2
    assert num_operations(inventory, 'remove_assets') == 1

    inventory.commit("Remove dir recursively")
    assert not asset_file.exists()
    assert not newdir2.exists()
    assert not newdir1.exists()


def test_move_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    emptydir = newdir1 / "empty"
    asset_file = newdir2 / "asset_file"
    asset = Asset(some_key="some_value",
                  type="TYPE",
                  make="MAKER",
                  model="MODEL",
                  serial="SERIAL",
                  other=1,
                  directory=newdir2
                  )
    inventory.add_asset(asset)
    inventory.add_directory(emptydir)
    inventory.commit("First asset added")

    # raise on non-dir:
    pytest.raises(ValueError, inventory.move_directory, asset_file, repo.git.root / "doesnotexist")
    pytest.raises(ValueError, inventory.move_directory, asset_file, (repo.git.root / "isafile").touch())
    # raise on rename:
    pytest.raises(InvalidInventoryOperation, inventory.move_directory, newdir2, newdir1)

    inventory.move_directory(newdir2, emptydir)
    assert num_operations(inventory, 'move_directories') == 1
    assert (newdir2, emptydir) == inventory.operations[0].operands

    # nothing happened on disc yet:
    assert newdir2.is_dir()
    assert not (emptydir / newdir2.name).exists()

    # TODO diff

    # now commit:
    inventory.commit("Move a directory")
    assert not newdir2.exists()
    assert repo.is_inventory_dir(emptydir / newdir2.name)


def test_rename_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    emptydir = newdir1 / "empty"
    asset_file = newdir2 / "asset_file"
    asset = Asset(some_key="some_value",
                  type="TYPE",
                  make="MAKER",
                  model="MODEL",
                  serial="SERIAL",
                  other=1,
                  directory=newdir2
                  )
    inventory.add_asset(asset)
    inventory.add_directory(emptydir)
    inventory.commit("First asset added")

    new_place = repo.git.root / "new_place"
    # raise on non-dir:
    pytest.raises(ValueError, inventory.rename_directory, asset_file, new_place)
    # raise on existing destination:
    pytest.raises(InvalidInventoryOperation, inventory.rename_directory, newdir1, emptydir)
    # raise on move:
    pytest.raises(InvalidInventoryOperation, inventory.rename_directory, newdir2, new_place)

    new_name = newdir1 / "new_name"
    inventory.rename_directory(newdir2, new_name)
    assert num_operations(inventory, 'rename_directories') == 1
    assert (newdir2, new_name) == inventory.operations[0].operands

    # nothing happened on disc yet:
    assert newdir2.is_dir()
    assert not new_name.exists()

    # TODO: diff

    # now commit:
    inventory.commit("Renamed directory")
    assert not newdir2.exists()
    assert repo.is_inventory_dir(new_name)


def test_add_asset_dir(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)

    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = Asset(some_key="some_value",
                  other=1,
                  type="TYPE",
                  make="MAKE",
                  model="MODEL",
                  serial="SERIAL",
                  is_asset_directory=True,
                  path=asset_dir_path
                  )

    # TODO: THIS NEEDS TESTING WITH NON-COMPLIANT DIRECTORY NAME BEFORE -> implicit rename operation!

    inventory.add_asset(asset)
    # operations to add new asset and a dir are registered:
    assert num_operations(inventory, 'new_assets') == 1
    assert num_operations(inventory, 'new_directories') == 1
    operands = [op.operands for op in inventory.operations]
    assert all(isinstance(o, tuple) for o in operands)
    assert (asset_dir_path,) in operands
    assert (asset,) in operands

    # nothing executed yet:
    assert not asset_dir_path.exists()

    # execute
    inventory.commit("add asset dir")
    assert inventory.repo.git.is_clean_worktree()
    # dir and yaml file are created:
    assert asset_dir_path.is_dir()
    assert (asset_dir_path / OnyoRepo.ASSET_DIR_FILE).is_file()
    # an asset dir is both - an inventory directory and an asset:
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_dir(asset_dir_path)
    # TODO: should the yaml file within be a valid asset path as well? Think not.
    # assert inventory.repo.is_asset_path(asset_dir_path / OnyoRepo.ASSET_DIR_FILE)

    # add asset aspect to existing directory, which does not yet comply with asset naming scheme
    dir_path = inventory.root / "newdir"
    inventory.add_directory(dir_path)
    inventory.commit("New inventory dir")

    asset = Asset(some_key="some_value",
                  other=1,
                  type="TYPE1",
                  make="MAKE1",
                  model="MODEL1",
                  serial="1X2",
                  is_asset_directory=True,
                  path=dir_path
                  )
    expected_name = "{type}_{make}_{model}.{serial}".format(**asset)
    expected_path = dir_path.parent / expected_name
    inventory.add_asset(asset)

    # registered operations:
    # 1. new asset
    assert num_operations(inventory, 'new_assets') == 1
    # 2. rename dir
    assert num_operations(inventory, 'rename_directories') == 1
    operands = [op.operands for op in inventory.operations]
    assert all(isinstance(o, tuple) for o in operands)
    assert (asset,) in operands
    assert (dir_path, expected_path) in operands

    # nothing done on disc yet
    assert inventory.repo.is_inventory_dir(dir_path)
    assert not inventory.repo.is_asset_path(dir_path)
    assert not inventory.repo.is_asset_dir(expected_path)
    assert not expected_path.exists()

    # execute
    inventory.commit("Turn inventory dir into asset dir")

    assert not inventory.repo.is_inventory_dir(dir_path)
    assert not inventory.repo.is_asset_path(dir_path)
    assert not dir_path.exists()

    assert expected_path.exists()
    assert inventory.repo.is_inventory_dir(expected_path)
    assert inventory.repo.is_asset_path(expected_path)
    assert inventory.repo.is_asset_dir(expected_path)
    assert inventory.repo.git.is_clean_worktree()


def test_remove_asset_dir_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = Asset(some_key="some_value",
                  other=1,
                  type="TYPE",
                  make="MAKE",
                  model="MODEL",
                  serial="SERIAL",
                  is_asset_directory=True,
                  path=asset_dir_path
                  )
    inventory.add_asset(asset)
    inventory.commit("Whatever")

    inventory.remove_directory(asset_dir_path)
    # Nothing done on disc yet:
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert asset_dir_path.is_dir()
    assert num_operations(inventory, 'remove_directories') == 1
    assert (asset_dir_path,) == inventory.operations[0].operands

    inventory.commit("Remove dir from asset dir")
    assert not inventory.repo.is_asset_dir(asset_dir_path)
    assert not inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert asset_dir_path.is_file()
    assert inventory.repo.git.is_clean_worktree()


def test_remove_asset_dir_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = Asset(some_key="some_value",
                  other=1,
                  type="TYPE",
                  make="MAKE",
                  model="MODEL",
                  serial="SERIAL",
                  is_asset_directory=True,
                  path=asset_dir_path
                  )
    inventory.add_asset(asset)
    inventory.commit("Whatever")

    # TODO: What if there are assets within? Auto-recurse? Switch?
    #       Operation needs to be atomic. Hence, must be empty!
    # TODO: What about an implicit remove_directory?
    #       -> NOPE! That would mean to not be able to disentangle the two ever again, because this operation will be
    #       recorded with this meaning.
    inventory.remove_asset(asset)

    # Nothing done on disc yet:
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_path(asset_dir_path)
    # Operation registered
    assert num_operations(inventory, 'remove_assets') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert asset in inventory.operations[0].operands

    # Execute:
    inventory.commit("Turn asset dir into plain dir")
    # It's still an inventory dir:
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    # but not an asset anymore:
    assert not inventory.repo.is_asset_path(asset_dir_path)
    assert not (asset_dir_path / OnyoRepo.ASSET_DIR_FILE).exists()
    assert inventory.repo.git.is_clean_worktree()


def test_move_asset_dir(repo: OnyoRepo) -> None:
    # An asset dir could be moved by either move_dir or move_asset. Since it's both, there's no difference when we treat
    # it as either one.

    # TODO: Similar to rename, moving an asset dir needs to record two operations, while technically executing only one.
    #       That is true for move_directory as well as move_asset
    #       For both - rename and move - it's also possible to actually register two operations, but turn the directory
    #       operation into a noop executor (but normal recorder) in case of an asset dir. However, that would somewhat
    #       imply that such calls are only valid as an internal operation rather than an arbitrary caller calling
    #       `move_directory(asset_dir)`. This in turn would suggest an ad-hoc "empty" Operation object instead of
    #       internally calling `move_directory`! This might be the nicest approach so far.

    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    dir_path = inventory.root / "destination"
    asset = Asset(some_key="some_value",
                  other=1,
                  type="TYPE",
                  make="MAKE",
                  model="MODEL",
                  serial="SERIAL",
                  is_asset_directory=True,
                  path=asset_dir_path
                  )
    inventory.add_asset(asset)
    inventory.add_directory(dir_path)
    inventory.commit("Whatever")

    inventory.move_asset(asset_dir_path, dir_path)
    assert num_operations(inventory, 'move_assets') == 1
    assert (asset_dir_path, dir_path) == inventory.operations[0].operands

    # nothing done on disc yet:
    assert inventory.repo.is_asset_dir(asset_dir_path)
    assert asset_dir_path.is_dir()
    assert not (dir_path / asset_dir_path.name).exists()

    inventory.commit("Move asset dir")
    new_path = dir_path / asset_dir_path.name
    assert not asset_dir_path.exists()
    assert inventory.repo.is_asset_dir(new_path)

    # Now move back but via `move_directory` instead.
    inventory.move_directory(new_path, inventory.root)
    assert num_operations(inventory, 'move_directories') == 1
    assert (new_path, inventory.root) == inventory.operations[0].operands

    # nothing done on disc
    assert inventory.repo.is_asset_dir(new_path)
    assert not asset_dir_path.exists()

    inventory.commit("Move asset dir back")

    assert inventory.repo.is_asset_dir(asset_dir_path)
    assert not new_path.exists()


def test_rename_asset_dir(repo: OnyoRepo) -> None:
    # While an asset dir is both - an asset and a dir - it can't be renamed by a rename_dir operations, because it
    # needs to comply to the naming scheme configuration for assets. For renaming we can't treat it as just a dir.
    # However, renaming the asset must also rename the dir. While on disc there's no difference, this would need to be
    # recorded separately!
    # TODO: This needs to be dealt with by the recorder generating an entry for both operations while technically only
    # rename_asset is executed.

    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = Asset(some_key="some_value",
                  other=1,
                  type="TYPE",
                  make="MAKE",
                  model="MODEL",
                  serial="SERIAL",
                  is_asset_directory=True,
                  path=asset_dir_path
                  )
    inventory.add_asset(asset)
    inventory.commit("Whatever")

    # renaming the asset dir as a dir needs to fail
    pytest.raises(ValueError, inventory.rename_directory, asset_dir_path, "newname")

    # renaming as an asset by changing the naming config
    inventory.repo.git.set_config("onyo.assets.filename", "{serial}_{other}", "onyo")
    inventory.repo.git.stage_and_commit(inventory.root / OnyoRepo.ONYO_CONFIG, "Change asset name config")
    new_asset_dir_path = asset_dir_path.parent / "SERIAL_1"

    inventory.rename_asset(asset_dir_path)
    # no change on disc:
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert inventory.repo.is_asset_dir(asset_dir_path)
    assert inventory.repo.git.is_clean_worktree()

    # operation registered
    assert num_operations(inventory, 'rename_assets') == 1
    assert (asset_dir_path, new_asset_dir_path) == inventory.operations[0].operands

    # execute
    inventory.commit("rename asset dir")
    assert not asset_dir_path.exists()
    assert inventory.repo.is_asset_dir(new_asset_dir_path)
    assert inventory.repo.is_asset_path(new_asset_dir_path)
    assert inventory.repo.is_inventory_dir(new_asset_dir_path)
    assert inventory.repo.git.is_clean_worktree()


def test_modify_asset_dir(repo: OnyoRepo) -> None:
    # This should make no difference to modify any other asset

    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_path = newdir2 / "TYPE_MAKER_MODEL.SERIAL"
    asset = Asset(some_key="some_value",
                  type="TYPE",
                  make="MAKER",
                  model="MODEL",
                  serial="SERIAL",
                  other=1,
                  is_asset_directory=True,
                  path=asset_path
                  )
    inventory.add_asset(asset)
    inventory.commit("asset dir added")
    assert inventory.repo.is_asset_dir(asset_path)

    asset_changes = Asset(some_key="new_value",  # arbitrary content change
                          model="CORRECTED-MODEL"  # implies rename w/ default name config
                          )
    new_asset = asset.copy()
    new_asset.update(asset_changes)
    new_asset.pop('path')

    inventory.modify_asset(asset, new_asset)
    # modify operation:
    assert num_operations(inventory, 'modify_assets') == 1
    new_asset_path = newdir2 / "TYPE_MAKER_CORRECTED-MODEL.SERIAL"
    assert (asset, new_asset) == inventory.operations[0].operands
    # implicit rename operation:
    assert num_operations(inventory, 'rename_assets') == 1
    assert (asset_path, new_asset_path) == inventory.operations[1].operands

    # nothing done on disc yet:
    assert inventory.repo.is_asset_dir(asset_path)
    assert not new_asset_path.exists()
    assert asset == Asset(**repo.get_asset_content(asset_path))
    assert inventory.repo.git.is_clean_worktree()

    # now commit:
    inventory.commit("Modify an asset")
    assert not asset_path.exists()
    assert inventory.repo.is_asset_dir(new_asset_path)
    assert inventory.repo.git.is_clean_worktree()

    expected_asset = Asset(**new_asset)
    expected_asset['path'] = new_asset_path
    assert repo.get_asset_content(new_asset_path) == expected_asset
