import pytest

from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    RESERVED_KEYS,
)
from onyo.lib.items import Item
from onyo.lib.inventory import Inventory
from onyo.lib.pseudokeys import PSEUDO_KEYS

from . import check_commit_msg
from ..commands import onyo_unset


@pytest.mark.ui({'yes': True})
def test_onyo_unset_errors(inventory: Inventory) -> None:
    """Raise the correct error in different illegal or impossible calls."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"

    # unset on non-existing asset
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[inventory.root / "not-existing" / "TYPE_MAKER_MODEL.SERIAL"],
                  keys=[key])

    # unset outside the repository
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[(inventory.root / "..").resolve()],
                  keys=[key])

    # unset without keys specified
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[asset_path],
                  keys=[])

    # unset on ".anchor"
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[inventory.root / "somewhere" / ANCHOR_FILE_NAME],
                  keys=[key])

    # unset on .git/
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[inventory.root / ".git"],
                  keys=[key])

    # unset on .onyo/
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[inventory.root / ".onyo"],
                  keys=[key])

    # no error scenario leaves the git worktree unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_name_fields_error(inventory: Inventory) -> None:
    """Raise when requested to unset a reserved name field."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()
    illegal_fields = ["type",
                      "make",
                      "model.name",
                      "serial"]

    # unset on illegal fields
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_unset,
                      inventory,
                      assets=[asset_path],
                      keys=[illegal])
        # name fields are still in the asset
        assert all(f"{subkey}:" in asset_path.read_text() for subkey in illegal.split('.'))

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_illegal_fields(inventory: Inventory) -> None:
    """Raise an error when requested to unset an illegal/reserverd field."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    old_hexsha = inventory.repo.git.get_hexsha()

    illegal_fields = RESERVED_KEYS + list(PSEUDO_KEYS.keys())

    # unset on illegal fields errors
    for illegal in illegal_fields:
        pytest.raises(ValueError,
                      onyo_unset,
                      inventory,
                      assets=[asset_path],
                      keys=[illegal])

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_errors_before_unset(inventory: Inventory) -> None:
    """Raise an error and do not modify/commit if a path is not valid."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    non_existing_asset_path = inventory.root / "non-existing" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_unset,
                  inventory,
                  assets=[asset_path,
                          non_existing_asset_path],
                  keys=[key])

    # no new asset was created
    assert not non_existing_asset_path.exists()
    assert non_existing_asset_path not in inventory.repo.git.files
    # the valid asset was not modified either
    assert key in asset_path.read_text()
    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.parametrize('message', ["", None, "message with spe\"cial\\char\'acteஞrs"])
@pytest.mark.parametrize('auto_message', [True, False])
def test_onyo_unset_simple(inventory: Inventory,
                           message,
                           auto_message) -> None:
    """Unset a key in an asset."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # check key exists
    assert key in inventory.repo.get_asset_content(asset_path).keys()

    # unset a value
    onyo_unset(inventory,
               assets=[asset_path],
               keys=[key],
               message=message,
               auto_message=auto_message)

    # check key was removed
    assert key not in inventory.repo.get_asset_content(asset_path).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()
    check_commit_msg(inventory, message, auto_message, "unset [")


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test\nsome_key: value"])
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
               assets=[asset_path1,
                       asset_path2],
               keys=[key])

    # check key was removed in both assets
    assert key not in inventory.repo.get_asset_content(asset_path1).keys()
    assert key not in inventory.repo.get_asset_content(asset_path2).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_allows_asset_duplicates(inventory: Inventory) -> None:
    """Do not error when the same asset is passed multiple times."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_unset()` with asset duplicates
    onyo_unset(inventory,
               assets=[asset_path, asset_path, asset_path],
               keys=[key])

    # check content
    assert key not in inventory.repo.get_asset_content(asset_path).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test\nother_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_unset_non_existing_keys(inventory: Inventory) -> None:
    """Unset a non-existing key does not error."""

    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    other_key = "other_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # trying to remove a non-existing key in an asset that does not exist does not error
    assert other_key not in inventory.repo.get_asset_content(asset_path1).keys()
    onyo_unset(inventory,
               assets=[asset_path1],
               keys=[other_key])

    # no commit was added
    assert inventory.repo.git.get_hexsha() == old_hexsha

    # trying to remove a key in two assets, but just one contains the key does not error
    assert other_key not in inventory.repo.get_asset_content(asset_path1).keys()
    assert other_key in inventory.repo.get_asset_content(asset_path2).keys()
    onyo_unset(inventory,
               assets=[asset_path1,
                       asset_path2],
               keys=[other_key])

    # the key was removed in asset_path2
    assert other_key not in inventory.repo.get_asset_content(asset_path2).keys()

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_allows_key_duplicates(inventory: Inventory) -> None:
    """Unsetting the same key multiple times does not error."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    key = "some_key"
    old_hexsha = inventory.repo.git.get_hexsha()

    # call `onyo_unset()` with key duplicates
    onyo_unset(inventory,
               assets=[asset_path],
               keys=[key, key, key])

    # check content
    assert key not in inventory.repo.get_asset_content(asset_path).keys()
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_unset_asset_dir(inventory: Inventory) -> None:
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
    onyo_unset(inventory,
               assets=[asset_dir],
               keys=['other', 'some_key'])
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    assert 'other' not in inventory.get_item(asset_dir)
    assert 'some_key' not in inventory.get_item(asset_dir)


@pytest.mark.ui({'yes': True})
def test_onyo_unset_empty(inventory: Inventory) -> None:
    """Cannot unset empty dicts, empty lists, and None values."""

    # Note: This is making sure onyo does not confuse an "empty value",
    #       w/ the key not being present.

    asset = Item(type="TYPE",
                 make="MAKE",
                 model=dict(name="MODEL"),
                 serial="SERIAL2",
                 directory=inventory.root)
    test_pairs = dict(emptydict=dict(),
                      emptylist=list(),
                      novalue=None,
                      emptystring="")
    asset.update(**test_pairs)
    inventory.add_asset(asset)
    inventory.commit("add asset w/ empty values")
    old_hexsha = inventory.repo.git.get_hexsha()
    asset_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL2"
    asset_written = inventory.get_item(asset_path)

    assert all(asset_written[k] == v for k, v in test_pairs.items())

    onyo_unset(inventory,
               assets=[asset_path],
               keys=test_pairs.keys())
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    asset_written = inventory.get_item(asset_path)
    assert all(k not in asset_written.keys() for k in test_pairs.keys())
