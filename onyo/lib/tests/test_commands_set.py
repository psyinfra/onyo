from pathlib import Path

import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.lib.items import Item
from . import check_commit_msg
from ..commands import onyo_set


@pytest.mark.ui({'yes': True})
def test_onyo_set_errors(inventory: Inventory) -> None:
    r"""`onyo_set()` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}

    # set on non-existing asset
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / "not-existing" / "TYPE_MAKER_MODEL.SERIAL"],
                  keys=key_value)

    # set on non-asset
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / "somewhere"],
                  keys=key_value)

    # set outside the repository
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[(inventory.root / "..").resolve()],
                  keys=key_value)

    # set without keys specified
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[asset_path],
                  keys=[])

    # set on ".anchor"
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / "somewhere" / OnyoRepo.ANCHOR_FILE_NAME],
                  keys=key_value)

    # set on .git/
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / ".git"],
                  keys=key_value)

    # set on .onyo/
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / ".onyo"],
                  keys=key_value)

    # no error scenario leaves the git tree unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_empty_keys_or_values(inventory: Inventory) -> None:
    r"""Verify the correct behavior for empty keys or values in `onyo_set()`."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    # test different empty values error
    for empty in [{"": "value"},
                  {" ": "value"},
                  {"\t": "value"},
                  {"\n": "value"},
                  {"": ""},
                  {None: "value"},
                  ]:
        pytest.raises(ValueError,
                      onyo_set,
                      inventory,
                      assets=[asset_path],
                      keys=empty)

    # the above szenarios did not add any commit
    assert inventory.repo.git.get_hexsha() == old_hexsha

    # set a key with an empty value works
    onyo_set(inventory,
             assets=[asset_path],
             keys={"key": ""})

    # check content
    assert "key: ''" in asset_path.read_text()
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_illegal_fields(inventory: Inventory) -> None:
    r"""`onyo_set()` must raise an error when attempting to set an
    illegal/reserved field."""
    from onyo.lib.consts import RESERVED_KEYS
    from onyo.lib.pseudokeys import PSEUDO_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    illegal_keys = list(PSEUDO_KEYS.keys()) + RESERVED_KEYS
    illegal_keys.remove("onyo.is.directory")
    illegal_fields = [{k: "new_value"} for k in illegal_keys]

    # set on illegal fields
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_set,
                      inventory,
                      assets=[asset_path],
                      keys=illegal)

    # no illegal field was written
    assert "new_value" not in asset_path.read_text()
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_errors_before_set(inventory: Inventory) -> None:
    r"""`onyo_set()` must raise the correct error and is not allowed to
    modify/commit anything, if one of the specified paths is not valid.
    """
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    non_existing_asset_path = inventory.root / "non-existing" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[asset_path,
                          non_existing_asset_path],
                  keys=key_value)

    # no new asset was created
    assert not non_existing_asset_path.exists()
    assert non_existing_asset_path not in inventory.repo.git.files
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.parametrize('message', ["", None, "message with spe\"cial\\char\'acteஞrs"])
@pytest.mark.parametrize('auto_message', [True, False])
def test_onyo_set_simple(inventory: Inventory,
                         message,
                         auto_message) -> None:
    r"""`onyo_set()` sets a value in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in an asset
    onyo_set(inventory,
             assets=[asset_path],
             keys=key_value,
             message=message,
             auto_message=auto_message)

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
    check_commit_msg(inventory, message, auto_message, "set [")


@pytest.mark.ui({'yes': True})
def test_onyo_set_already_set(inventory: Inventory) -> None:
    r"""`onyo_set()` does not error if called with values
    that are already set."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"some_key": "some_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # check content is already set
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()

    # set a value in an asset
    onyo_set(inventory,
             assets=[asset_path],
             keys=key_value)

    # check content is unchanged
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()

    # no commit added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_overwrite_existing_value(inventory: Inventory) -> None:
    r"""`onyo_set()` overwrites an existing value with a new one in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    new_key_value = {"some_key": "that_new_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # check content
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()
    assert "that_new_value" not in inventory.repo.get_asset_content(asset_path).values()

    # set a value in an asset
    onyo_set(inventory,
             assets=[asset_path],
             keys=new_key_value)

    # check content
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" not in inventory.repo.get_asset_content(asset_path).values()
    assert "that_new_value" in inventory.repo.get_asset_content(asset_path).values()
    assert Path.read_text(asset_path).count("some_key") == 1

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_some_values_already_set(inventory: Inventory) -> None:
    r"""When `onyo_set()` is called with two key value pairs, and one
    is already set and the other not, onyo changes the second one
    without error.
    """
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    new_key_values = {"some_key": "some_value",  # exists in asset
                      "new_key": "new_value"}  # exists not in asset
    old_hexsha = inventory.repo.git.get_hexsha()

    # check content
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "new_key" not in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()
    assert "new_value" not in inventory.repo.get_asset_content(asset_path).values()

    # set a value in an asset
    onyo_set(inventory,
             assets=[asset_path],
             keys=new_key_values)

    # check content
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "new_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()
    assert "new_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_multiple(inventory: Inventory) -> None:
    r"""Modify multiple assets in a single call and with one commit."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in multiple assets at once
    onyo_set(inventory,
             assets=[asset_path1,
                     asset_path2],
             keys=key_value)

    # check contents
    assert "this_key" in inventory.repo.get_asset_content(asset_path1).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path1).values()
    assert "this_key" in inventory.repo.get_asset_content(asset_path2).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path2).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_allows_duplicates(inventory: Inventory) -> None:
    r"""Calling `onyo_set()` with a list containing the same asset multiple
    times does not error."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_set()` with `paths` containing duplicates
    onyo_set(inventory,
             assets=[asset_path, asset_path, asset_path],
             keys=key_value)

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_asset_dir(inventory: Inventory) -> None:
    asset = Item(some_key="some_value",
                 type="TYPE",
                 make="MAKER",
                 model=dict(name="MODEL"),
                 serial="SERIAL2",
                 other=1,
                 directory=inventory.root)
    asset["onyo.is.directory"] = True
    inventory.add_asset(asset)
    asset_dir = inventory.root / "TYPE_MAKER_MODEL.SERIAL2"
    inventory.commit("add an asset dir")
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in an asset dir
    onyo_set(inventory,
             assets=[asset_dir],
             keys={'other': 2})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.get_item(asset_dir)['other'] == 2

    # turn asset dir into asset file:
    onyo_set(inventory,
             assets=[asset_dir],
             keys={'onyo.is.directory': False})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~2') == old_hexsha
    assert inventory.repo.is_asset_path(asset_dir)
    assert asset_dir.is_file()
    assert inventory.get_item(asset_dir)["some_key"] == "some_value"

    # turn it back into an asset dir
    onyo_set(inventory,
             assets=[asset_dir],
             keys={'onyo.is.directory': True})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~3') == old_hexsha
    assert inventory.repo.is_asset_dir(asset_dir)
    assert inventory.get_item(asset_dir)["some_key"] == "some_value"


@pytest.mark.ui({'yes': True})
def test_set_empty_dictlist(inventory: Inventory) -> None:
    r"""`onyo_set` can set empty dicts and lists as values"""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    onyo_set(inventory, assets=[asset_path], keys={"new_key": dict()})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.get_item(asset_path)["new_key"] == dict()
    onyo_set(inventory, assets=[asset_path], keys={"new_key": list()})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.get_item(asset_path)["new_key"] == list()


@pytest.mark.ui({'yes': True})
@pytest.mark.repo_dirs("roundtrip")
def test_set_roundtrip(inventory: Inventory):
    asset_path = inventory.root / "roundtrip" / "atype_amake_amodelname.aserial"
    asset_content = """---
type: atype # comment 1

make: amake
model:
  name: amodelname # comment 2

serial: aserial
akey: # comment 3
"""
    asset_path.write_text(asset_content)
    inventory.repo.git.commit(asset_path, "Add raw formatted asset file")
    assert inventory.repo.git.is_clean_worktree()
    assert asset_content == asset_path.read_text()
    old_hexsha = inventory.repo.git.get_hexsha()

    # We have an asset file w/ blank lines and comments.
    # When we set a new value nothing but that value should change.
    onyo_set(inventory, assets=[asset_path], keys={'akey': 'avalue'})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert asset_content.replace("akey:", "akey: avalue") == asset_path.read_text()
