from pathlib import Path

import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
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
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set on non-asset
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / "somewhere"],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set outside the repository
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[(inventory.root / "..").resolve()],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set without keys specified
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[asset_path],
                  keys=[],
                  message="some subject\n\nAnd a body")

    # set on ".anchor"
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / "somewhere" / OnyoRepo.ANCHOR_FILE_NAME],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set on .git/
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / ".git"],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

    # set on .onyo/
    pytest.raises(ValueError,
                  onyo_set,
                  inventory,
                  assets=[inventory.root / ".onyo"],
                  keys=key_value,
                  message="some subject\n\nAnd a body")

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
                      keys=empty,
                      message="some subject\n\nAnd a body")

    # the above szenarios did not add any commit
    assert inventory.repo.git.get_hexsha() == old_hexsha

    # set a key with an empty value works
    onyo_set(inventory,
             assets=[asset_path],
             keys={"key": ""},
             message="some subject\n\nAnd a body")

    # check content
    assert "key: ''" in asset_path.read_text()
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_illegal_fields(inventory: Inventory) -> None:
    r"""`onyo_set()` must raise an error when requested to set an
    illegal/reserverd field without `rename=True`."""
    from onyo.lib.consts import RESERVED_KEYS, PSEUDO_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    illegal_keys = PSEUDO_KEYS + RESERVED_KEYS + inventory.repo.get_asset_name_keys()
    # TODO: Remove is_asset_directory from RESERVED_KEYS altogether?
    illegal_keys.remove("is_asset_directory")
    illegal_fields = [{k: "new_value"} for k in illegal_keys]

    # set on illegal fields
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_set,
                      inventory,
                      assets=[asset_path],
                      keys=illegal,
                      message="some subject\n\nAnd a body")

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
    r"""`onyo_set()` sets a value in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in an asset
    onyo_set(inventory,
             assets=[asset_path],
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
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test"])
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
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_asset_dir(inventory: Inventory) -> None:
    inventory.add_asset(dict(some_key="some_value",
                             type="TYPE",
                             make="MAKER",
                             model="MODEL",
                             serial="SERIAL2",
                             other=1,
                             directory=inventory.root,
                             is_asset_directory=True)
                        )
    asset_dir = inventory.root / "TYPE_MAKER_MODEL.SERIAL2"
    inventory.commit("add an asset dir")
    old_hexsha = inventory.repo.git.get_hexsha()

    # set a value in an asset dir
    onyo_set(inventory,
             assets=[asset_dir],
             keys={'other': 2})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.get_asset(asset_dir)['other'] == 2

    # turn asset dir into asset file:
    onyo_set(inventory,
             assets=[asset_dir],
             keys={'is_asset_directory': False})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~2') == old_hexsha
    assert inventory.repo.is_asset_path(asset_dir)
    assert asset_dir.is_file()
    assert inventory.get_asset(asset_dir)["some_key"] == "some_value"

    # turn it back into an asset dir
    onyo_set(inventory,
             assets=[asset_dir],
             keys={'is_asset_directory': True})
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~3') == old_hexsha
    assert inventory.repo.is_asset_dir(asset_dir)
    assert inventory.get_asset(asset_dir)["some_key"] == "some_value"
