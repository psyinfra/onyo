import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_unset


@pytest.mark.ui({'yes': True})
def test_onyo_unset_errors(inventory: Inventory) -> None:
    """`onyo_unset` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"

    # unset on non-existing asset
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[inventory.root / "not-existing" / "TYPE_MAKER_MODEL.SERIAL"],
                  keys=[key],
                  message="some subject\n\nAnd a body")

    # unset outside the repository
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[(inventory.root / "..").resolve()],
                  keys=[key],
                  message="some subject\n\nAnd a body")

    # unset without keys specified
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[asset_path],
                  keys=[],
                  message="some subject\n\nAnd a body")

    # unset on ".anchor"
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[inventory.root / "somewhere" / OnyoRepo.ANCHOR_FILE_NAME],
                  keys=[key],
                  message="some subject\n\nAnd a body")

    # unset on .git/
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[inventory.root / ".git"],
                  keys=[key],
                  message="some subject\n\nAnd a body")

    # unset on .onyo/
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[inventory.root / ".onyo"],
                  keys=[key],
                  message="some subject\n\nAnd a body")

    # no error scenario leaves the git worktree unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_name_fields_error(inventory: Inventory) -> None:
    """`onyo_unset` must raise an error when requested to unset a
    reserved name field."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()
    illegal_fields = ["type",
                      "make",
                      "model",
                      "serial"]

    # unset on illegal fields
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_unset,
                      inventory,
                      paths=[asset_path],
                      keys=[illegal],
                      message="some subject\n\nAnd a body")
        # name fields are still in the asset
        assert illegal in asset_path.read_text()

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_illegal_fields(inventory: Inventory) -> None:
    """`onyo_unset` must raise an error when requested to unset an
    illegal/reserverd field."""
    from onyo.lib.consts import RESERVED_KEYS, PSEUDO_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    illegal_fields = RESERVED_KEYS + PSEUDO_KEYS

    # unset on illegal fields errors
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_unset,
                      inventory,
                      paths=[asset_path],
                      keys=[illegal],
                      message="some subject\n\nAnd a body")

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_errors_before_unset(inventory: Inventory) -> None:
    """`onyo_unset` must raise the correct error and is not allowed to
    modify/commit anything, if one of the specified paths is not valid.
    """
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    non_existing_asset_path = inventory.root / "non-existing" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  paths=[asset_path,
                         non_existing_asset_path],
                  keys=[key],
                  message="some subject\n\nAnd a body")

    # no new asset was created
    assert not non_existing_asset_path.exists()
    assert non_existing_asset_path not in inventory.repo.git.files
    # the valid asset was not modified either
    assert key in asset_path.read_text()
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_simple(inventory: Inventory) -> None:
    """Unset a key in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # check key exists
    assert key in inventory.repo.get_asset_content(asset_path).keys()

    # unset a value
    onyo_unset(inventory,
               paths=[asset_path],
               keys=[key],
               message="some subject\n\nAnd a body")

    # check key was removed
    assert key not in inventory.repo.get_asset_content(asset_path).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_unset_multiple(inventory: Inventory) -> None:
    """Modify multiple assets in a single call and with one commit."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # check key exists in both assets
    assert key in inventory.repo.get_asset_content(asset_path1).keys()
    assert key in inventory.repo.get_asset_content(asset_path2).keys()

    # create a new directory
    onyo_unset(inventory,
               paths=[asset_path1,
                      asset_path2],
               keys=[key],
               message="some subject\n\nAnd a body")

    # check key was removed in both assets
    assert key not in inventory.repo.get_asset_content(asset_path1).keys()
    assert key not in inventory.repo.get_asset_content(asset_path2).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_allows_asset_duplicates(inventory: Inventory) -> None:
    """Calling `onyo_unset()` with a list containing the same asset
    multiple times does not error."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_unset()` with asset duplicates
    onyo_unset(inventory,
               paths=[asset_path, asset_path, asset_path],
               keys=[key],
               message="some subject\n\nAnd a body")

    # check content
    assert key not in inventory.repo.get_asset_content(asset_path).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nother_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_unset_non_existing_keys(inventory: Inventory) -> None:
    """Calling `onyo_unset()` on a non-existing key does not error."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    other_key = "other_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # trying to remove a non-existing key in an asset that does not exist does not error
    assert other_key not in inventory.repo.get_asset_content(asset_path1).keys()
    onyo_unset(inventory,
               paths=[asset_path1],
               keys=[other_key],
               message="some subject\n\nAnd a body")

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha

    # trying to remove a key in two assets, but just one contains the key does not error
    assert other_key not in inventory.repo.get_asset_content(asset_path1).keys()
    assert other_key in inventory.repo.get_asset_content(asset_path2).keys()
    onyo_unset(inventory,
               paths=[asset_path1,
                      asset_path2],
               keys=[other_key],
               message="some subject\n\nAnd a body")

    # the key was removed in asset_path2
    assert other_key not in inventory.repo.get_asset_content(asset_path2).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_allows_key_duplicates(inventory: Inventory) -> None:
    """Calling `onyo_unset()` with the same key multiple times does not error."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_unset()` with key duplicates
    onyo_unset(inventory,
               paths=[asset_path],
               keys=[key, key, key],
               message="some subject\n\nAnd a body")

    # check content
    assert key not in inventory.repo.get_asset_content(asset_path).keys()
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_asset_dir(inventory: Inventory) -> None:
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
    onyo_unset(inventory,
               paths=[asset_dir],
               keys=['other', 'some_key'])
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert 'other' not in inventory.get_asset(asset_dir)
    assert 'some_key' not in inventory.get_asset(asset_dir)
