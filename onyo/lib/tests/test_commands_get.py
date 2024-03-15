from pathlib import Path

import pytest

from onyo.lib.filters import Filter
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_get


@pytest.mark.ui({'yes': True})
def test_onyo_get_errors(inventory: Inventory) -> None:
    """`onyo_get()` must raise the correct error in different illegal or impossible calls."""

    # get on non-existing asset
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  paths=[inventory.root / "not-existing" / "TYPE_MAKER_MODEL.SERIAL"])

    # get outside the repository
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  paths=[(inventory.root / "..")])

    # get with negative depth value
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  depth=-1)

    # get on ".anchor"
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  paths=[inventory.root / "somewhere" / OnyoRepo.ANCHOR_FILE_NAME])

    # get on .git/
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  paths=[inventory.root / ".git"])

    # get on .onyo/
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  paths=[inventory.root / ".onyo"])


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nempty_key: ''"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_empty_keys(inventory: Inventory,
                             capsys) -> None:
    """Verify `onyo_get()` prints values for non-existing keys as unset,
    and values for keys that exist but have an empty value correctly."""
    from onyo.lib.consts import UNSET_VALUE
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    missing_key = "asdf"
    empty_key = "empty_key"

    # call `onyo_get()` requesting a key that does not exist
    assert missing_key not in Path.read_text(asset_path1)
    onyo_get(inventory,
             paths=[asset_path1],
             keys=[missing_key, "path"])

    # verify output
    output1 = capsys.readouterr().out
    assert UNSET_VALUE in output1
    assert asset_path1.name in output1

    # call `onyo_get()` requesting a key that exists, but has no value set
    assert empty_key in Path.read_text(asset_path2)
    onyo_get(inventory,
             paths=[asset_path2],
             keys=[empty_key, "path"])

    # verify output
    output2 = capsys.readouterr().out
    assert UNSET_VALUE not in output2
    assert asset_path2.name in output2


@pytest.mark.ui({'yes': True})
def test_onyo_get_on_empty_directory(inventory: Inventory) -> None:
    """`onyo_get()` does not error when called on a valid but empty directory."""
    dir_path = inventory.root / 'empty'

    # `onyo_get()` on a directory without assets does not error
    onyo_get(inventory,
             paths=[dir_path])


@pytest.mark.ui({'yes': True})
def test_onyo_get_reserved_keys(inventory: Inventory,
                                capsys) -> None:
    """`onyo_get()` allows to specify all reserved keys to query
    and display information for."""
    from onyo.lib.consts import RESERVED_KEYS, PSEUDO_KEYS
    reserved = ["type", "make", "model", "serial"] + PSEUDO_KEYS + RESERVED_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # get on reserved fields
    for reserved_key in reserved:
        keys = [reserved_key]
        if reserved_key != "path":
            keys.append("path")
        # verify that the key is in the header
        onyo_get(inventory, keys=keys)
        assert reserved_key in capsys.readouterr().out
        # verify asset is returned
        onyo_get(inventory, keys=keys, machine_readable=True)
        assert asset_path.name in capsys.readouterr().out


@pytest.mark.ui({'yes': True})
def test_onyo_get_name_keys(inventory: Inventory,
                            capsys) -> None:
    """If no keys are specified when calling `onyo_get()`
    the name keys are printed by default."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    name_keys = ["type", "make", "model", "serial"]

    # call `onyo_get()` without keys specified
    onyo_get(inventory,
             paths=[asset_path])

    # verify output
    output = capsys.readouterr().out
    assert asset_path.name in output
    for name_key in name_keys:
        assert name_key in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_errors_before_get(inventory: Inventory) -> None:
    """`onyo_get()` must raise the correct error if one of
    the specified paths is not valid.
    """
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    non_existing_asset_path = inventory.root / "non-existing" / "TYPE_MAKER_MODEL.SERIAL"

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  paths=[asset_path,
                         non_existing_asset_path])


@pytest.mark.ui({'yes': True})
def test_onyo_get_simple(inventory: Inventory,
                         capsys) -> None:
    """`onyo_get()` gets a value in an asset."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    get_key = "some_key"

    # get a value in an asset
    onyo_get(inventory,
             paths=[asset_path],
             keys=[get_key, "path"])

    # verify output
    output = capsys.readouterr().out
    assert asset_path.name in output
    assert get_key in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_machine_readable(inventory: Inventory,
                                   capsys) -> None:
    """`onyo_get()` with machine_readable=True gives different
    output that contains all requested information."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    get_key = "some_key"

    # call `onyo_get()` without machine readable mode
    onyo_get(inventory,
             paths=[asset_path],
             keys=[get_key, "path"])

    standard_output = capsys.readouterr().out

    # call `onyo_get()` in machine readable mode
    onyo_get(inventory,
             paths=[asset_path],
             keys=[get_key, "path"],
             machine_readable=True)

    # verify output contains the correct information but is different from normal mode
    machine_readable_output = capsys.readouterr().out
    assert machine_readable_output != standard_output
    assert asset_path.name in machine_readable_output
    # machine_readable does not print headers, just the values
    assert "some_value" in machine_readable_output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_sorting(inventory: Inventory,
                          capsys) -> None:
    """`onyo_get()` allows different types of sorting the output,
    but errors if illegal sorting is specified."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    get_key = "some_key"

    # call `onyo_get()` with sort=ascending
    onyo_get(inventory,
             sort="ascending",
             keys=[get_key, "path"])
    ascending_output = capsys.readouterr().out

    # call `onyo_get()` with sort=descending
    onyo_get(inventory,
             sort="descending",
             keys=[get_key, "path"])
    descending_output = capsys.readouterr().out

    # verify output contains the correct information but is different depending on sorting
    assert ascending_output != descending_output
    assert asset_path1.name in ascending_output
    assert asset_path2.name in ascending_output
    assert get_key in ascending_output
    assert asset_path1.name in descending_output
    assert asset_path2.name in descending_output
    assert get_key in descending_output

    # call `onyo_get()` with illegal sort keyword errors
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  sort="ILLEGAL",
                  keys=[get_key, "path"])


@pytest.mark.ui({'yes': True})
def test_onyo_get_on_directory(inventory: Inventory,
                               capsys) -> None:
    """`onyo_get()` gets a value in assets inside a directory."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / "somewhere"
    get_key = "some_key"

    # call `onyo_get()` on a directory
    onyo_get(inventory,
             paths=[dir_path],
             keys=[get_key, "path"])

    # verify output contains the asset inside the directory
    output = capsys.readouterr().out
    assert asset_path.name in output
    assert get_key in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_match(inventory: Inventory,
                        capsys) -> None:
    """`onyo_get()` lists just matching assets when `match` is used."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    matches = [Filter("other=1").match]
    get_key = "some_key"

    # both assets have `get_key`, but just one asset matches
    assert get_key in inventory.repo.get_asset_content(asset_path1).keys()
    assert get_key in inventory.repo.get_asset_content(asset_path2).keys()

    # get a value just in the matching asset, but specify both paths
    onyo_get(inventory,
             paths=[asset_path1, asset_path2],
             match=matches,  # pyre-ignore[6]
             keys=[get_key, "path"])

    # verify output contains just information for matching assets
    output = capsys.readouterr().out
    assert asset_path1.name in output
    assert output.count(get_key) == 1
    assert asset_path2.name not in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_no_matches(inventory: Inventory,
                             capsys) -> None:
    """`onyo_get()` behaves correctly when `match` matches no assets."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    matches = [Filter("unfound=values").match]

    # `onyo_get()` is called, but no assets match
    onyo_get(inventory,
             match=matches)  # pyre-ignore[6]

    # verify output contains no assets because nothing matched
    output = capsys.readouterr().out
    assert "No assets matching the filter(s) were found" in output
    assert asset_path1.name not in output
    assert asset_path2.name not in output
    assert "path" not in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_multiple(inventory: Inventory,
                           capsys) -> None:
    """`onyo_get()` finds information about multiple assets in a single call."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    get_key = "some_key"

    # get a value in multiple assets at once
    onyo_get(inventory,
             paths=[asset_path1,
                    asset_path2],
             keys=[get_key, "path"])

    # verify output contains all assets and "path" as default key
    output = capsys.readouterr().out
    assert asset_path1.name in output
    assert asset_path2.name in output
    assert "path" in output
    assert get_key in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_depth(inventory: Inventory,
                        capsys) -> None:
    """`onyo_get()` with depth selects the correct assets."""
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"

    # get a value using depth
    onyo_get(inventory,
             paths=[inventory.root],
             depth=1)

    # verify output contains all assets and "path" as default key
    output = capsys.readouterr().out
    assert asset_path1.name not in output
    assert asset_path2.name in output
    assert "path" in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_depth_zero(inventory: Inventory,
                             capsys) -> None:
    """Calling `onyo_get(depth=0)` is legal and selects all assets from all subpaths."""
    onyo_get(inventory,
             paths=[inventory.root],
             depth=0)

    # verify output contains all assets and "path" as default key
    output = capsys.readouterr().out
    for asset in inventory.repo.get_asset_paths():
        assert asset.name in output
    assert "path" in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_default_inventory_root(inventory: Inventory,
                                         capsys) -> None:
    """Calling `onyo_get()` without path uses inventory.root as default
    and selects all assets of the inventory."""
    onyo_get(inventory)

    # verify output contains all assets and "path" as default key
    output = capsys.readouterr().out
    for asset in inventory.repo.get_asset_paths():
        assert asset.name in output
    assert "path" in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_allows_duplicates(inventory: Inventory,
                                    capsys) -> None:
    """Calling `onyo_get()` with a list containing the same asset multiple
    times does not error, but displays information just once."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # call `onyo_get()` with `paths` containing duplicates
    onyo_get(inventory,
             paths=[asset_path, asset_path, asset_path])

    # verify output contains all assets and "path" as default key
    output = capsys.readouterr().out
    assert output.count(asset_path.name) == 1


def test_onyo_get_asset_dir(inventory: Inventory,
                            capsys) -> None:
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
    onyo_get(inventory, match=[Filter("other=1").match])
    assert str(asset_dir.relative_to(inventory.root)) in capsys.readouterr().out
