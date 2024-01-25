import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_set


@pytest.mark.ui({'yes': True})
def test_onyo_set_errors(inventory: Inventory) -> None:
    """`onyo_set` must raise the correct error in different illegal or impossible calls."""
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


@pytest.mark.ui({'yes': True})
def test_onyo_set_on_empty_directory(inventory: Inventory) -> None:
    """`onyo_set` does not error when called on a valid but empty directory,
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


@pytest.mark.ui({'yes': True})
def test_onyo_set_illegal_fields(inventory: Inventory) -> None:
    """`onyo_set` must raise an error when requested to set an
    illegal/reserverd field without `rename=True`."""
    # TODO: add PSEUDO_KEYS after fixing BUG #527:
    from onyo.lib.consts import RESERVED_KEYS  # PSEUDO_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    illegal_fields = [
        {"type": "new_value"},
        {"make": "new_value"},
        {"model": "new_value"},
        {"serial": "new_value"}]
    # TODO: add PSEUDO_KEYS after fixing BUG #527:
    # illegal_fields.extend([{k : "new_value"} for k in PSEUDO_KEYS])
    illegal_fields.extend([{k: "new_value"} for k in RESERVED_KEYS])

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


@pytest.mark.ui({'yes': True})
def test_onyo_set_errors_before_set(inventory: Inventory) -> None:
    """`onyo_set` must raise the correct error and is not allowed to
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
    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_simple(inventory: Inventory) -> None:
    """Set a value in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # create a new directory
    onyo_set(inventory,
             paths=[asset_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_set_multiple(inventory: Inventory) -> None:
    """Modify multiple assets in a single call and with one commit."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # create a new directory
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
    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_set_allows_duplicates(inventory: Inventory) -> None:
    """Calling `onyo_set()` with a list containing the same asset multiple
    times does not error."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key_value = {"this_key": "that_value"}
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_set()` with `dirs` containing duplicates
    onyo_set(inventory,
             paths=[asset_path, asset_path, asset_path],
             keys=key_value,  # pyre-ignore[6]
             message="some subject\n\nAnd a body")

    # check content
    assert "this_key" in inventory.repo.get_asset_content(asset_path).keys()
    assert "that_value" in inventory.repo.get_asset_content(asset_path).values()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()
