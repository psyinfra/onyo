from pathlib import Path

import pytest

from onyo.lib.filters import Filter
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_set


@pytest.mark.ui({'yes': True})
def test_onyo_set_errors(inventory: Inventory) -> None:
    """`onyo_set()` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}

    # set on non-existing asset
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[inventory.root / "not-existing" / "TYPE_MAKER_MODEL.SERIAL"],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set outside the repository
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[(inventory.root / "..").resolve()],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set without keys specified
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[asset_path],
                  keys=[],
                  message="some subject\n\nAnd a body")

    # set with negative depth value
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[asset_path],
                  keys=key_value,
                  depth=-1,
                  message="some subject\n\nAnd a body")

    # set on ".anchor"
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[inventory.root / "somewhere" / OnyoRepo.ANCHOR_FILE_NAME],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set on .git/
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[inventory.root / ".git"],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set on .onyo/
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  paths=[inventory.root / ".onyo"],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # no error scenario leaves the git tree unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_empty_keys_or_values(inventory: Inventory) -> None:
    """Verify the correct behavior for empty keys or values in `onyo_set()`."""
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
                      paths=[asset_path],
                      keys=empty,
                      message="some subject\n\nAnd a body")

    # the above szenarios did not add any commit
    assert inventory.repo.git.get_hexsha() == old_hexsha

    # set a key with an empty value works
    onyo_set(inventory,
             paths=[asset_path],
             keys={"key": ""},
             message="some subject\n\nAnd a body")

    # check content
    assert "key: ''" in asset_path.read_text()
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_directory(inventory: Inventory) -> None:
    """`onyo_set()` sets a value in an asset when called on a directory."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / "somewhere"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value for a directory
    onyo_set(inventory,
             paths=[dir_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_on_empty_directory(inventory: Inventory) -> None:
    """`onyo_set()` does not error when called on a valid but empty directory,
    but no commits are added."""
    dir_path = inventory.root / 'empty'
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set on a directory without assets
    onyo_set(inventory,
             paths=[dir_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_illegal_fields(inventory: Inventory) -> None:
    """`onyo_set()` must raise an error when requested to set an
    illegal/reserverd field without `rename=True`."""
    from onyo.lib.consts import RESERVED_KEYS, PSEUDO_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    illegal_fields = [
        {"type": "new_value"},
        {"make": "new_value"},
        {"model": "new_value"},
        {"serial": "new_value"}]
    illegal_fields.extend([{k: "new_value"} for k in PSEUDO_KEYS + RESERVED_KEYS])

    # set on illegal fields
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_set,
                      inventory,
                      paths=[asset_path],
                      keys=illegal,
                      message="some subject\n\nAnd a body")

    # no illegal field was written
    assert "new_value" not in asset_path.read_text()
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_errors_before_set(inventory: Inventory) -> None:
    """`onyo_set()` must raise the correct error and is not allowed to
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
                  paths=[asset_path,
                         non_existing_asset_path],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # no new asset was created
    assert not non_existing_asset_path.exists()
    assert non_existing_asset_path not in inventory.repo.git.files
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_simple(inventory: Inventory) -> None:
    """`onyo_set()` sets a value in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in an asset
    onyo_set(inventory,
             paths=[asset_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_already_set(inventory: Inventory) -> None:
    """`onyo_set()` does not error if called with values
    that are already set."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"some_key": "some_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # check content is already set
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()

    # set a value in an asset
    onyo_set(inventory,
             paths=[asset_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content is unchanged
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()

    # no commit added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_overwrite_existing_value(inventory: Inventory) -> None:
    """`onyo_set()` overwrites an existing value with a new one in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    new_key_value = {"some_key": "that_new_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # check content
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()
    assert "that_new_value" not in inventory.repo.get_asset_content(asset_path).values()

    # set a value in an asset
    onyo_set(inventory,
             paths=[asset_path],
             keys=new_key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

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
    """When `onyo_set()` is called with two key value pairs, and one
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
             paths=[asset_path],
             keys=new_key_values,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "some_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "new_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "some_value" in inventory.repo.get_asset_content(asset_path).values()
    assert "new_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nold_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_match(inventory: Inventory) -> None:
    """`onyo_set()` updates the correct assets when `match` is used."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    matches = [Filter("old_key=value").match]
    key_value = {"new_key": "new_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # verify that one asset contains the "old_key" to match and the other not
    assert "old_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "old_key" in inventory.repo.get_asset_content(asset_path2).keys()
    # the new key is not yet in either asset
    assert "new_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "new_key" not in inventory.repo.get_asset_content(asset_path2).keys()

    # set a value just in the matching asset, but specify both paths
    onyo_set(inventory,
             paths=[asset_path1, asset_path2],
             match=matches,  # pyre-ignore[6]
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content is just set in the matching asset, the other is unchanged
    assert "new_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "new_key" in inventory.repo.get_asset_content(asset_path2).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_no_matches(inventory: Inventory) -> None:
    """`onyo_set()` behaves correctly when `match` matches no assets."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    matches = [Filter("unfound=values").match]
    key_value = {"new_key": "new_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # verify that both assets don't contain neither "new_key" nor "unfound"
    assert "new_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "new_key" not in inventory.repo.get_asset_content(asset_path2).keys()
    assert "unfound" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "unfound" not in inventory.repo.get_asset_content(asset_path2).keys()

    # `onyo_set()` is called, but neither asset match so nothing will be set
    onyo_set(inventory,
             paths=[asset_path1, asset_path2],
             match=matches,  # pyre-ignore[6]
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content is not set in either asset because neither matched
    assert "new_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "new_key" not in inventory.repo.get_asset_content(asset_path2).keys()

    # no commit was added because nothing matched
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_multiple(inventory: Inventory) -> None:
    """Modify multiple assets in a single call and with one commit."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in multiple assets at once
    onyo_set(inventory,
             paths=[asset_path1,
                    asset_path2],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check contents
    assert "this_key" in inventory.repo.get_asset_content(asset_path1).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path1).values()
    assert "this_key" in inventory.repo.get_asset_content(asset_path2).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path2).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_depth(inventory: Inventory) -> None:
    """`onyo_set()` with depth selects the correct assets."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # check key does not exist in either asset
    assert "this_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "this_key" not in inventory.repo.get_asset_content(asset_path2).keys()

    # set a value using depth
    onyo_set(inventory,
             paths=[inventory.root],
             keys=key_value,  # pyre-ignore[6]
             depth=1,
             message="some subject\n\nAnd a body")

    # check key was set only in one asset:
    assert "this_key" not in inventory.repo.get_asset_content(asset_path1).keys()
    assert "this_key" in inventory.repo.get_asset_content(asset_path2).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_depth_zero(inventory: Inventory) -> None:
    """Calling `onyo_set(depth=0)` is legal and selects
    all assets from all subpaths."""
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # check key does not exist
    for asset in inventory.repo.get_asset_paths():
        assert "this_key" not in inventory.repo.get_asset_content(asset).keys()

    # set a value
    onyo_set(inventory,
             keys=key_value,  # pyre-ignore[6]
             paths=[inventory.root],
             depth=0,
             message="some subject\n\nAnd a body")

    # check key was set in all assets
    for asset in inventory.repo.get_asset_paths():
        assert "this_key" in inventory.repo.get_asset_content(asset).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_default_inventory_root(inventory: Inventory) -> None:
    """Calling `onyo_set()` without path uses inventory.root as default
    and selects all assets of the inventory."""
    key = {"new_key": "new_me"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value without giving a path
    onyo_set(inventory,
             keys=key,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check key was set in all assets
    for asset in inventory.repo.get_asset_paths():
        assert "new_key" in inventory.repo.get_asset_content(asset).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_allows_duplicates(inventory: Inventory) -> None:
    """Calling `onyo_set()` with a list containing the same asset multiple
    times does not error."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_set()` with `paths` containing duplicates
    onyo_set(inventory,
             paths=[asset_path, asset_path, asset_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
