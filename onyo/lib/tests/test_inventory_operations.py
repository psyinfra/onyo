import pytest
from copy import deepcopy

from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    ASSET_DIR_FILE_NAME,
    RESERVED_KEYS,
)
from onyo.lib.pseudokeys import (
    PSEUDO_KEYS,
    PSEUDOKEY_ALIASES,
)
from onyo.lib.exceptions import (
    InvalidInventoryOperationError,
    NoopError,
    NotADirError,
    NotAnAssetError
)
from onyo.lib.inventory import Inventory, OPERATIONS_MAPPING
from onyo.lib.onyo import OnyoRepo
from onyo.lib.items import (
    Item,
    ItemSpec,
)


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
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other='1',
                     directory=newdir2,
                     type="test",
                     make="I",
                     model=dict(name="mk1"),
                     serial="123")
    assert num_operations(inventory, 'new_assets') == 0
    assert num_operations(inventory, 'new_directories') == 0

    inventory.add_asset(asset)

    # operations to add new asset and two dirs are registered:
    assert num_operations(inventory, 'new_assets') == 1
    assert num_operations(inventory, 'new_directories') == 2
    operands = [op.operands for op in inventory.operations]
    assert all(isinstance(o, tuple) for o in operands)
    assert (newdir1,) in operands
    assert (newdir2,) in operands

    # assertions on the item in registered operation:
    item_operands = [op[0] for op in operands if isinstance(op[0], Item)]
    assert len(item_operands) == 1
    assert item_operands[0].equal_content(asset)
    assert item_operands[0]["onyo.path.absolute"] == asset_file

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
    asset_from_disc = inventory.get_item(asset_file)
    assert asset_file == asset_from_disc.get('onyo.path.absolute')
    # All pseudo-keys are set, except `onyo.is.empty` which is only set for directories:
    assert all(asset_from_disc[k] is not None for k in PSEUDO_KEYS.keys() if k != 'onyo.is.empty')
    for k, v in asset.items():
        if k not in RESERVED_KEYS + list(PSEUDO_KEYS.keys()):
            assert asset_from_disc[k] == v
    assert asset_from_disc['onyo.path.file'] == asset_from_disc['onyo.path.relative'] == asset_file.relative_to(inventory.root)
    assert asset_from_disc['onyo.is.asset'] is True
    assert asset_from_disc['onyo.is.directory'] is False
    assert asset_from_disc['onyo.is.empty'] is None

    # check operations record:
    commit = [c for c in inventory.get_history(asset_file, n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'new_assets':
            assert v == [asset_file.relative_to(inventory.root)]
        elif k == 'new_directories':
            assert newdir1.relative_to(inventory.root) in v
            assert newdir2.relative_to(inventory.root) in v
        else:
            assert v == []
    # history pseudo-keys:
    assert asset_from_disc['onyo.was.created.hexsha'] == asset_from_disc['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()

    # required keys must not be empty
    asset.update(dict(model=dict(name="")))
    pytest.raises(ValueError, inventory.add_asset, asset)

    # required keys must not be None
    asset.update(dict(model=dict(name=None)))
    pytest.raises(ValueError, inventory.add_asset, asset)

    # To be added Asset requires a path:
    asset = dict(a_key='a_value')
    pytest.raises(ValueError, inventory.add_asset, asset)

    # Asset must not yet exist:  (TODO: This may be wrong. Seems better if it must not yet exist as an asset,
    #                                   but may exist as an untracked file! Note, that this is not testing a command,
    #                                   but an inventory operation.)
    existing_asset_file = repo.git.root / 'root_asset'
    existing_asset_file.touch()
    asset = {'some': 'whatever', 'onyo.path.absolute': existing_asset_file}
    pytest.raises(ValueError, inventory.add_asset, asset)

    # TODO: should also fail when adding an asset that is already pending? Or one that is also being removed, etc?


def test_remove_asset(inventory: Inventory) -> None:
    # NOTE: First trial using inventory fixture

    doesnotexist = inventory.root / "root_asset"
    pytest.raises(NotAnAssetError, inventory.remove_asset, Item(doesnotexist, repo=inventory.repo))

    isadir = inventory.root / "a_dir"
    isadir.mkdir()
    pytest.raises(NotAnAssetError, inventory.remove_asset, Item(isadir, repo=inventory.repo))

    # TODO: Can't remove untracked?? See similar cases in new_asset, new_dir

    # TODO: We should get such paths from the fixture! Otherwise it doesn't make things easier.
    asset_file = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    assert asset_file.exists()

    asset = inventory.get_item(asset_file)
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

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'remove_assets':
            assert v == [asset_file.relative_to(inventory.root)]
        else:
            assert v == []


def test_move_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_file = newdir2 / "test_I_mk1.123"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other='1',
                     directory=newdir2,
                     type="test",
                     make="I",
                     model=dict(name="mk1"),
                     serial="123")

    inventory.add_asset(asset)
    inventory.commit("First asset added")
    # get item bound to inventory, implying pseudokeys are evaluated against that inventory:
    asset = inventory.get_item(asset_file)

    # non-existing destination raises:
    pytest.raises(ValueError, inventory.move_asset, asset, inventory.get_item(newdir1 / "doesnotexist"))

    # move to same place:
    pytest.raises(ValueError, inventory.move_asset, asset, inventory.get_item(newdir2))

    # valid target:
    inventory.move_asset(asset, inventory.get_item(newdir1))
    assert num_operations(inventory, 'move_assets') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert asset_file in inventory.operations[0].operands
    assert newdir1 in inventory.operations[0].operands
    moved_asset_path = newdir1 / asset_file.name
    # nothing done on disc yet:
    assert asset_file.is_file()
    assert not moved_asset_path.exists()

    # TODO: test diff

    # now commit:
    inventory.commit("Move an asset")
    assert not asset_file.exists()
    assert moved_asset_path.is_file()

    # check operations record:
    commit = [c for c in inventory.get_history(moved_asset_path, n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'move_assets':
            assert v == [(
                asset_file.relative_to(inventory.root), moved_asset_path.relative_to(inventory.root)
            )]
        else:
            assert v == []
    asset_from_disc = inventory.get_item(moved_asset_path)

    # history pseudo-keys: The move is not an asset modification:
    assert asset_from_disc['onyo.was.created.hexsha'] == asset_from_disc['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')


def test_rename_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    spec = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     type="TYPE",
                     make="MAKER",
                     model=dict(name="MODEL"),
                     serial="SERIAL",
                     other='1',
                     directory=newdir2)
    inventory.add_asset(spec)
    inventory.commit("First asset added")
    asset = inventory.get_item(newdir2 / inventory.generate_asset_name(spec))

    # rename to itself raises:
    pytest.raises(NoopError, inventory.rename_asset, asset)

    # invalid name according to default config:
    del asset['type']
    pytest.raises(ValueError, inventory.rename_asset, asset)

    # Note: No commit here. Valid rename only via modify ATM. Hence, tested in modify asset instead.
    # Alternative: Modify file directly instead and rename here?


def test_modify_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_file = newdir2 / "TYPE_MAKER_MODEL.SERIAL"
    spec = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     type="TYPE",
                     make="MAKER",
                     model=dict(name="MODEL"),
                     serial="SERIAL",
                     other='1',
                     directory=newdir2)
    inventory.add_asset(spec)
    inventory.commit("First asset added")
    asset = inventory.get_item(newdir2 / inventory.generate_asset_name(spec))

    asset_changes = dict(some_key="new_value",  # arbitrary content change
                         model=dict(name="")  # empty required key
                         )
    new_asset = deepcopy(asset)
    new_asset.update(asset_changes)

    # required keys must not be empty
    pytest.raises(ValueError, inventory.modify_asset, asset, new_asset)
    # required keys must not be None
    new_asset.update(model=dict(name=None))
    pytest.raises(ValueError, inventory.modify_asset, asset, new_asset)

    new_asset.update(dict(model=dict(name="CORRECTED-MODEL")))  # implies rename w/ default name config

    # Asset path in `new_asset` must be None or identical to `asset`:
    new_asset['onyo.path.absolute'] = newdir2 / "new_name"
    pytest.raises(ValueError, inventory.modify_asset, asset, new_asset)
    new_asset['onyo.path.absolute'] = None
    # raises on non-existing asset
    pytest.raises(ValueError, inventory.modify_asset, Item(repo.git.root / "doesnotexist", repo=inventory.repo), new_asset)
    # raises on non-asset
    pytest.raises(ValueError, inventory.modify_asset, Item(newdir1, repo=inventory.repo), new_asset)

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
    asset_on_disc = inventory.get_item(asset_file)
    assert asset_file == asset_on_disc.get('onyo.path.absolute')
    for k, v in asset.items():
        if k not in RESERVED_KEYS + list(PSEUDO_KEYS.keys()):
            assert asset_on_disc[k] == v

    # TODO: diff

    # now commit:
    inventory.commit("Modify an asset")
    assert not asset_file.exists()
    assert repo.is_asset_path(new_asset_file)

    asset_on_disc = inventory.get_item(new_asset_file)
    for k, v in new_asset.items():
        if k not in PSEUDO_KEYS:
            assert asset_on_disc[k] == new_asset[k]

    assert asset_on_disc['onyo.path.absolute'] == new_asset_file
    assert asset_on_disc['onyo.path.parent'] == new_asset_file.parent.relative_to(inventory.root)
    assert asset_on_disc['onyo.path.file'] == asset_on_disc['onyo.path.relative'] == new_asset_file.relative_to(inventory.root)
    assert asset_on_disc['onyo.is.directory'] is False
    assert asset_on_disc['onyo.is.asset'] is True
    assert asset_on_disc['onyo.is.empty'] is None

    # check operations record:
    commit = [c for c in inventory.get_history(new_asset_file, n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'modify_assets':
            assert v == [asset_file.relative_to(inventory.root)]
        elif k == 'rename_assets':
            assert v == [(asset_file.relative_to(inventory.root), new_asset_file.relative_to(inventory.root))]
        else:
            assert v == []

    # history pseudo-keys:
    assert asset_on_disc['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()
    assert asset_on_disc['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')


def test_add_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)

    # can not add non-inventory paths:
    invalid_inventory_dir = Item(repo.git.root / '.git' / 'new', repo=repo)
    pytest.raises(ValueError, inventory.add_directory, invalid_inventory_dir)

    new_dir = Item(repo.git.root / 'newdir', repo=repo)
    inventory.add_directory(new_dir)

    # operation is registered:
    assert num_operations(inventory, 'new_directories') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert new_dir['onyo.path.absolute'] in inventory.operations[0].operands

    # nothing done on disk yet:
    assert not new_dir['onyo.path.absolute'].exists()

    # TODO: diff

    # now commit
    inventory.commit("Add new directory")
    assert repo.is_inventory_dir(new_dir['onyo.path.absolute'])
    assert new_dir['onyo.path.file'].is_file()

    # check operations record:
    commit = [c for c in inventory.get_history(new_dir['onyo.path.file'], n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'new_directories':
            assert v == [new_dir['onyo.path.relative']]
        else:
            assert v == []

    # pseudo-keys
    assert new_dir['onyo.is.directory'] is True
    assert new_dir['onyo.is.asset'] is False
    assert new_dir['onyo.is.empty'] is True
    assert new_dir['onyo.path.file'] == new_dir['onyo.path.relative'] / ANCHOR_FILE_NAME
    assert new_dir['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha()


def test_remove_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    emptydir = newdir1 / "empty"
    does_not_exist = repo.git.root / 'does' / 'not' / 'exist'
    asset_file = newdir2 / "TYPE_MAKE_MODEL.SERIAL"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     type="TYPE",
                     make="MAKE",
                     model=dict(name="MODEL"),
                     serial="SERIAL",
                     other='1',
                     directory=newdir2)
    inventory.add_asset(asset)
    inventory.add_directory(Item(emptydir, repo=repo))
    inventory.commit("First asset added")

    # raise on asset file
    pytest.raises(NoopError, inventory.remove_directory, Item(asset_file, repo=repo))
    # raise on non-dir
    pytest.raises(InvalidInventoryOperationError, inventory.remove_directory, Item(does_not_exist, repo=repo))

    emptydir_item = inventory.get_item(emptydir)
    inventory.remove_directory(emptydir_item)
    assert num_operations(inventory, 'remove_directories') == 1
    assert isinstance(inventory.operations[0].operands, tuple)
    assert emptydir_item in inventory.operations[0].operands

    # nothing done on disc yet:
    assert emptydir.is_dir()

    # TODO: diff

    # now commit
    inventory.commit("Remove directory")
    assert not emptydir.exists()

    # recursive
    inventory.remove_directory(Item(newdir1, repo=repo))
    assert num_operations(inventory, 'remove_directories') == 2
    assert num_operations(inventory, 'remove_assets') == 1

    inventory.commit("Remove dir recursively")
    assert not asset_file.exists()
    assert not newdir2.exists()
    assert not newdir1.exists()

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'remove_directories':
            assert newdir1.relative_to(inventory.root) in v
            assert newdir2.relative_to(inventory.root) in v
            assert len(v) == 2
        elif k == 'remove_assets':
            assert v == [asset_file.relative_to(inventory.root)]
        else:
            assert v == []


def test_move_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    emptydir = newdir1 / "empty"
    asset_file = newdir2 / "asset_file"
    spec = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                    some_key="some_value",
                    type="TYPE",
                    make="MAKER",
                    model=dict(name="MODEL"),
                    serial="SERIAL",
                    other=1,
                    directory=newdir2)
    inventory.add_asset(spec)
    inventory.add_directory(Item(emptydir, repo=repo))
    inventory.commit("First asset added")
    asset = inventory.get_item(asset_file)

    # raise on non-dir:
    pytest.raises(ValueError,
                  inventory.move_directory, asset, inventory.get_item(repo.git.root / "doesnotexist"))
    pytest.raises(ValueError,
                  inventory.move_directory, asset, inventory.get_item((repo.git.root / "isafile").touch()))
    # raise on rename:
    pytest.raises(InvalidInventoryOperationError,
                  inventory.move_directory, inventory.get_item(newdir2), inventory.get_item(newdir1))

    inventory.move_directory(inventory.get_item(newdir2), inventory.get_item(emptydir))
    assert num_operations(inventory, 'move_directories') == 1
    assert (newdir2, emptydir) == inventory.operations[0].operands

    # nothing happened on disc yet:
    assert newdir2.is_dir()
    moved_dir = emptydir / newdir2.name
    assert not moved_dir.exists()

    # TODO diff

    # now commit:
    inventory.commit("Move a directory")
    assert not newdir2.exists()
    assert repo.is_inventory_dir(moved_dir)

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'move_directories':
            assert v == [(
                newdir2.relative_to(inventory.root), moved_dir.relative_to(inventory.root)
            )]
        else:
            assert v == []

    # pseudo-keys
    newdir_item = Item(moved_dir, repo=inventory.repo)
    assert newdir_item['onyo.is.directory'] is True
    assert newdir_item['onyo.is.asset'] is False
    assert newdir_item['onyo.is.empty'] is False  # There's an asset within
    assert newdir_item['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()
    assert newdir_item['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')


def test_rename_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    emptydir = newdir1 / "empty"
    asset_file = newdir2 / "asset_file"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     type="TYPE",
                     make="MAKER",
                     model=dict(name="MODEL"),
                     serial="SERIAL",
                     other=1,
                     directory=newdir2)
    inventory.add_asset(asset)
    inventory.add_directory(Item(emptydir, repo=repo))
    inventory.commit("First asset added")

    new_place = repo.git.root / "new_place"
    # raise on non-dir:
    pytest.raises(ValueError, inventory.rename_directory, Item(asset_file, repo=repo), new_place)
    # raise on existing destination:
    pytest.raises(InvalidInventoryOperationError, inventory.rename_directory, Item(newdir1, repo=repo), emptydir)
    # raise on move:
    pytest.raises(InvalidInventoryOperationError, inventory.rename_directory, Item(newdir2, repo=repo), new_place)

    new_name = newdir1 / "new_name"
    inventory.rename_directory(Item(newdir2, repo=repo), new_name)
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

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'rename_directories':
            assert v == [(
                newdir2.relative_to(inventory.root), new_name.relative_to(inventory.root)
            )]
        else:
            assert v == []

    # pseudo-keys
    newdir_item = Item(new_name, repo=inventory.repo)
    assert newdir_item['onyo.is.directory'] is True
    assert newdir_item['onyo.is.asset'] is False
    assert newdir_item['onyo.is.empty'] is False  # There's an asset within
    assert newdir_item['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()
    assert newdir_item['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')


def test_add_asset_dir(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)

    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other=1,
                     type="TYPE",
                     make="MAKE",
                     model=dict(name="MODEL"),
                     serial="SERIAL")
    asset["onyo.path.absolute"] = asset_dir_path
    asset["onyo.is.directory"] = True
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
    assert (asset_dir_path / ASSET_DIR_FILE_NAME).is_file()
    # an asset dir is both - an inventory directory and an asset:
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_dir(asset_dir_path)
    # TODO: should the yaml file within be a valid asset path as well? Think not.
    # assert inventory.repo.is_asset_path(asset_dir_path / OnyoRepo.ASSET_DIR_FILE)
    # check operations record:
    commit = [c for c in inventory.get_history((asset_dir_path / ASSET_DIR_FILE_NAME), n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'new_directories':
            assert v == [asset_dir_path.relative_to(inventory.root)]
        elif k == 'new_assets':
            assert v == [asset_dir_path.relative_to(inventory.root)]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(asset_dir_path)
    assert asset_from_disk['onyo.path.relative'] == asset_dir_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ASSET_DIR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is True
    assert asset_from_disk['onyo.was.modified.hexsha'] == asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha()

    # add asset aspect to existing directory, which does not yet comply with asset naming scheme
    dir_path = inventory.root / "newdir"
    inventory.add_directory(Item(dir_path, repo=repo))
    inventory.commit("New inventory dir")

    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other=1,
                     type="TYPE1",
                     make="MAKE1",
                     model=dict(name="MODEL1"),
                     serial="1X2")
    asset["onyo.path.absolute"] = dir_path
    asset["onyo.is.directory"] = True
    expected_name = inventory.generate_asset_name(asset)
    expected_path = dir_path.parent / expected_name
    inventory.add_asset(asset)

    # registered operations:
    # 1. new asset
    assert num_operations(inventory, 'new_assets') == 1
    # 2. rename dir
    assert num_operations(inventory, 'rename_directories') == 1
    operands = [op.operands for op in inventory.operations]
    assert all(isinstance(o, tuple) for o in operands)

    item_operands = [op[0] for op in operands if isinstance(op[0], Item)]
    assert len(item_operands) == 1
    assert item_operands[0].equal_content(asset)
    assert item_operands[0]["onyo.path.absolute"] == expected_path

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

    # check operations record:
    commit = [c for c in inventory.get_history(expected_path / ASSET_DIR_FILE_NAME, n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'rename_directories':
            assert v == [(dir_path.relative_to(inventory.root), expected_path.relative_to(inventory.root))]
        elif k == 'new_assets':
            assert v == [expected_path.relative_to(inventory.root)]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(expected_path)
    assert asset_from_disk['onyo.path.relative'] == expected_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ASSET_DIR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is True
    # Note: 'onyo.was.created.*' considers the last commit with 'new_assets'/'new_directories' records:
    #       Not clear yet, whether that is what we want.
    assert asset_from_disk['onyo.was.modified.hexsha'] == asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha()


def test_add_dir_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    spec = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                    some_key="some_value",
                    other=1,
                    type="TYPE1",
                    make="MAKE1",
                    model=dict(name="MODEL1"),
                    serial="1X2",
                    directory=inventory.root)
    inventory.add_asset(spec)
    inventory.commit("Add an asset.")
    asset_path = inventory.root / "TYPE1_MAKE1_MODEL1.1X2"
    asset = inventory.get_item(asset_path)

    # Add directory aspect to existing asset:
    inventory.add_directory(asset)

    # registered operation:
    assert len(inventory.operations) == 1
    assert num_operations(inventory, 'new_directories') == 1
    operands = [op.operands for op in inventory.operations]
    assert all(isinstance(o, tuple) for o in operands)
    assert (asset_path,) in operands
    # nothing executed yet:
    assert asset_path.is_file()

    inventory.commit("Turn asset into asset dir")
    assert inventory.repo.is_asset_dir(asset_path)
    assert inventory.repo.git.is_clean_worktree()

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'new_directories':
            assert v == [asset_path.relative_to(inventory.root)]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(asset_path)
    assert asset_from_disk['onyo.path.relative'] == asset_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ASSET_DIR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is True
    # Note: 'onyo.was.created.*' considers the last commit with 'new_assets'/'new_directories' records:
    #       Not clear yet, whether that is what we want.
    assert asset_from_disk['onyo.was.modified.hexsha'] == asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha()


def test_remove_asset_dir_directory(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other=1,
                     type="TYPE",
                     make="MAKE",
                     model=dict(name="MODEL"),
                     serial="SERIAL")
    asset["onyo.path.absolute"] = asset_dir_path
    asset["onyo.is.directory"] = True
    inventory.add_asset(asset)
    asset_within = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                            type="a",
                            make="b",
                            model=dict(name="c"),
                            serial="1A",
                            directory=asset_dir_path)
    inventory.add_asset(asset_within)
    inventory.commit("Whatever")

    asset_dir_item = inventory.get_item(asset_dir_path)
    inventory.remove_directory(asset_dir_item)
    # Nothing done on disc yet:
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert asset_dir_path.is_dir()

    assert num_operations(inventory, 'remove_assets') == 1

    assert num_operations(inventory, 'remove_directories') == 1
    assert (inventory.get_item(asset_dir_path / 'a_b_c.1A'),) == inventory.operations[0].operands
    assert (asset_dir_item,) == inventory.operations[1].operands

    inventory.commit("Remove dir from asset dir")
    assert not inventory.repo.is_asset_dir(asset_dir_path)
    assert not inventory.repo.is_inventory_dir(asset_dir_path)
    assert not inventory.repo.is_asset_path(asset_dir_path / "a_b_c.1A")
    assert inventory.repo.is_asset_path(asset_dir_path)
    assert asset_dir_path.is_file()
    assert inventory.repo.git.is_clean_worktree()

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'remove_directories':
            assert v == [asset_dir_path.relative_to(inventory.root)]
        elif k == 'remove_assets':
            assert v == [(asset_dir_path / "a_b_c.1A").relative_to(inventory.root)]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(asset_dir_path)
    assert asset_from_disk['onyo.path.relative'] == asset_dir_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative']
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is False
    assert asset_from_disk['onyo.is.empty'] is None
    # Note: Removal of directory aspect doesn't count as asset modification:
    assert asset_from_disk['onyo.was.modified.hexsha'] == asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')


def test_remove_asset_dir_asset(repo: OnyoRepo) -> None:
    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other=1,
                     type="TYPE",
                     make="MAKE",
                     model=dict(name="MODEL"),
                     serial="SERIAL")
    asset["onyo.path.absolute"] = asset_dir_path
    asset["onyo.is.directory"] = True
    inventory.add_asset(asset)
    asset_within = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                            type="a",
                            make="b",
                            model=dict(name="c"),
                            serial="1A",
                            directory=asset_dir_path)
    inventory.add_asset(asset_within)
    inventory.commit("Whatever")
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
    assert inventory.repo.git.is_clean_worktree()
    # It's still an inventory dir:
    assert inventory.repo.is_inventory_dir(asset_dir_path)
    # but not an asset anymore:
    assert not inventory.repo.is_asset_path(asset_dir_path)
    assert not (asset_dir_path / ASSET_DIR_FILE_NAME).exists()
    # asset within unaffected:
    assert inventory.repo.is_asset_path(asset_within['directory'] / "a_b_c.1A")

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'remove_assets':
            assert v == [asset_dir_path.relative_to(inventory.root)]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(asset_dir_path)
    assert asset_from_disk['onyo.path.relative'] == asset_dir_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ANCHOR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is False
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is False  # asset_within still exists
    # Note: Removal of asset aspect doesn't count as directory modification:
    assert asset_from_disk['onyo.was.modified.hexsha'] == asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')


def test_move_asset_dir(repo: OnyoRepo) -> None:
    # An asset dir could be moved by either move_dir or move_asset. Since it's both, there's no difference when we treat
    # it as either one.

    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    dir_path = inventory.root / "destination"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other=1,
                     type="TYPE",
                     make="MAKE",
                     model=dict(name="MODEL"),
                     serial="SERIAL")
    asset["onyo.path.absolute"] = asset_dir_path
    asset["onyo.is.directory"] = True
    inventory.add_asset(asset)
    inventory.add_directory(Item(dir_path, repo=repo))
    inventory.commit("Whatever")
    asset_dir = inventory.get_item(asset_dir_path)

    inventory.move_asset(asset_dir, inventory.get_item(dir_path))
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

    # check operations record (two operations recorded):
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'move_assets':
            assert v == [(
                asset_dir_path.relative_to(inventory.root), (dir_path / asset_dir_path.name).relative_to(inventory.root)
            )]
        elif k == 'move_directories':
            assert v == [(
                asset_dir_path.relative_to(inventory.root), (dir_path / asset_dir_path.name).relative_to(inventory.root)
            )]
        else:
            assert v == []

    # Now move back but via `move_directory` instead.
    inventory.move_directory(inventory.get_item(new_path), inventory.get_item(inventory.root))
    assert num_operations(inventory, 'move_directories') == 1
    assert (new_path, inventory.root) == inventory.operations[0].operands

    # nothing done on disc
    assert inventory.repo.is_asset_dir(new_path)
    assert not asset_dir_path.exists()

    inventory.commit("Move asset dir back")
    assert inventory.repo.is_asset_dir(asset_dir_path)
    assert not new_path.exists()

    # check operations record (two operations recorded):
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'move_assets':
            assert v == [(
                (dir_path / asset_dir_path.name).relative_to(inventory.root), asset_dir_path.relative_to(inventory.root)
            )]
        elif k == 'move_directories':
            assert v == [(
                (dir_path / asset_dir_path.name).relative_to(inventory.root), asset_dir_path.relative_to(inventory.root)
            )]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(asset_dir_path)
    assert asset_from_disk['onyo.path.relative'] == asset_dir_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ASSET_DIR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is True
    assert asset_from_disk['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()
    assert asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~2')


def test_rename_asset_dir(repo: OnyoRepo) -> None:
    # While an asset dir is both - an asset and a dir - it can't be renamed by a rename_dir operations, because it
    # needs to comply to the naming scheme configuration for assets. For renaming we can't treat it as just a dir.
    # However, renaming the asset must also rename the dir. While on disc there's no difference, this needs to be
    # recorded separately!

    inventory = Inventory(repo)
    asset_dir_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL"
    asset = ItemSpec(alias_map=PSEUDOKEY_ALIASES,
                     some_key="some_value",
                     other=1,
                     type="TYPE",
                     make="MAKE",
                     model=dict(name="MODEL"),
                     serial="SERIAL")
    asset["onyo.path.absolute"] = asset_dir_path
    asset["onyo.is.directory"] = True
    inventory.add_asset(asset)
    inventory.commit("Whatever")

    asset_dir = inventory.get_item(asset_dir_path)

    # renaming the asset dir as a dir needs to fail
    pytest.raises(NotADirError, inventory.rename_directory, asset_dir, "newname")

    # renaming as an asset by changing the naming config
    inventory.repo.set_config("onyo.assets.name-format", "{serial}_{other}", "onyo")
    inventory.repo.commit(inventory.repo.onyo_config,
                          "Change asset name config")
    new_asset_dir_path = asset_dir_path.parent / "SERIAL_1"

    inventory.rename_asset(asset_dir)
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

    # check operations record (two operations recorded):
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'rename_assets':
            assert v == [(asset_dir_path.relative_to(inventory.root), new_asset_dir_path.relative_to(inventory.root))]
        elif k == 'rename_directories':
            assert v == [(asset_dir_path.relative_to(inventory.root), new_asset_dir_path.relative_to(inventory.root))]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(new_asset_dir_path)
    assert asset_from_disk['onyo.path.relative'] == new_asset_dir_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ASSET_DIR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is True
    assert asset_from_disk['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()
    assert asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~2')


def test_modify_asset_dir(repo: OnyoRepo) -> None:
    # This should make no difference to modifying any other asset

    inventory = Inventory(repo)
    newdir1 = repo.git.root / "somewhere"
    newdir2 = newdir1 / "new"
    asset_path = newdir2 / "TYPE_MAKE_MODEL.SERIAL"
    asset = ItemSpec(
        {"some_key": "some_value",
         "type": "TYPE",
         "make": "MAKE",
         "model": dict(name="MODEL"),
         "serial": "SERIAL",
         "other": 1,
         "onyo": {"is": {"asset": True,
                         "directory": True},
                  "path": {"absolute": asset_path}}
         },
        alias_map=PSEUDOKEY_ALIASES,
    )
    inventory.add_asset(asset)
    inventory.commit("asset dir added")
    asset = inventory.get_item(asset_path)
    assert inventory.repo.is_asset_dir(asset_path)
    assert asset['onyo.is.directory'] and asset['onyo.is.asset']

    asset_changes = dict(some_key="new_value",  # arbitrary content change
                         model=dict(name="CORRECTED-MODEL")  # implies rename w/ given name config
                         )
    new_asset = asset.copy()
    new_asset.update(asset_changes)
    new_asset['onyo.path.absolute'] = None

    inventory.modify_asset(asset, new_asset)
    # modify operation:
    assert num_operations(inventory, 'modify_assets') == 1
    new_asset_path = newdir2 / "TYPE_MAKE_CORRECTED-MODEL.SERIAL"
    assert (asset, new_asset) == inventory.operations[0].operands
    # implicit rename operation:
    assert num_operations(inventory, 'rename_assets') == 1
    assert (asset_path, new_asset_path) == inventory.operations[1].operands

    # nothing done on disc yet:
    assert inventory.repo.is_asset_dir(asset_path)
    assert not new_asset_path.exists()
    asset_on_disc = inventory.get_item(asset_path)
    for k1, v1 in asset_on_disc.items():
        assert asset[k1] == v1
    for k2, v2 in asset.items():
        assert asset_on_disc[k2] == v2
    assert inventory.repo.git.is_clean_worktree()

    # now commit:
    inventory.commit("Modify an asset")
    assert not asset_path.exists()
    assert inventory.repo.is_asset_dir(new_asset_path)
    assert inventory.repo.git.is_clean_worktree()

    asset_on_disc = inventory.get_item(new_asset_path)
    for k, v in new_asset.items():
        if k not in PSEUDO_KEYS:
            assert asset_on_disc[k] == new_asset[k]

    assert asset_on_disc['onyo.path.absolute'] == new_asset_path
    assert asset_on_disc['onyo.path.parent'] == new_asset_path.parent.relative_to(inventory.root)

    # check operations record:
    commit = [c for c in inventory.get_history(n=1)][0]
    for k, v in commit['operations'].items():
        if k == 'modify_assets':
            assert v == [asset_path.relative_to(inventory.root)]
        elif k == 'rename_assets':
            assert v == [(asset_path.relative_to(inventory.root), new_asset_path.relative_to(inventory.root))]
        elif k == 'rename_directories':
            assert v == [(asset_path.relative_to(inventory.root), new_asset_path.relative_to(inventory.root))]
        else:
            assert v == []

    # pseudo-keys
    asset_from_disk = inventory.get_item(new_asset_path)
    assert asset_from_disk['onyo.path.relative'] == new_asset_path.relative_to(inventory.root)
    assert asset_from_disk['onyo.path.file'] == asset_from_disk['onyo.path.relative'] / ASSET_DIR_FILE_NAME
    assert asset_from_disk['onyo.is.asset'] is True
    assert asset_from_disk['onyo.is.directory'] is True
    assert asset_from_disk['onyo.is.empty'] is True
    assert asset_from_disk['onyo.was.modified.hexsha'] == inventory.repo.git.get_hexsha()
    assert asset_from_disk['onyo.was.created.hexsha'] == inventory.repo.git.get_hexsha('HEAD~1')
