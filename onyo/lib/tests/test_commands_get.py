from pathlib import Path

import pytest

from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    TEMPLATE_DIR,
    UNSET_VALUE,
)
from onyo.lib.filters import Filter
from onyo.lib.inventory import Inventory
from onyo.lib.items import Item
from ..commands import onyo_get


@pytest.mark.ui({'yes': True})
def test_onyo_get_errors(inventory: Inventory) -> None:
    r"""Raise the correct error in different illegal or impossible calls."""

    # get on non-existing asset
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  include=[inventory.root / "not-existing" / "TYPE_MAKER_MODEL.SERIAL"])

    # get outside the repository
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  include=[(inventory.root / "..")])

    # get with negative depth value
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  depth=-1)

    # get on ".anchor"
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  include=[inventory.root / "somewhere" / ANCHOR_FILE_NAME])

    # get on .git/
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  include=[inventory.root / ".git"])

    # get on .onyo/
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  include=[inventory.root / ".onyo"])


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel: exists\nserial: test\nempty_key: ''"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_empty_keys(inventory: Inventory,
                             capsys) -> None:
    r"""Print <unset> for non-existing keys and keys with an empty value."""

    from onyo.lib.consts import UNSET_VALUE
    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    missing_key = "asdf"
    empty_key = "empty_key"

    # call `onyo_get()` requesting a key that does not exist
    assert missing_key not in Path.read_text(asset_path1)
    onyo_get(inventory,
             include=[asset_path1],
             keys=[missing_key, "onyo.path.relative"])

    # verify output
    output1 = capsys.readouterr().out
    assert UNSET_VALUE in output1
    assert asset_path1.name in output1

    # call `onyo_get()` requesting a key that exists, but has no value set
    assert empty_key in Path.read_text(asset_path2)
    onyo_get(inventory,
             include=[asset_path2],
             keys=[empty_key, "onyo.path.relative"])

    # verify output
    output2 = capsys.readouterr().out
    assert UNSET_VALUE in output2
    assert asset_path2.name in output2


@pytest.mark.ui({'yes': True})
def test_onyo_get_on_empty_directory(inventory: Inventory) -> None:
    r"""No error when called on a valid but empty directory."""

    dir_path = inventory.root / 'empty'

    # `onyo_get()` on a directory without assets does not error
    onyo_get(inventory,
             include=[dir_path])


@pytest.mark.ui({'yes': True})
def test_onyo_get_reserved_keys(inventory: Inventory,
                                capsys) -> None:
    r"""Get all reserved keys."""

    from onyo.lib.consts import RESERVED_KEYS
    from onyo.lib.pseudokeys import PSEUDO_KEYS
    reserved = ["type", "make", "model.name", "serial"] + list(PSEUDO_KEYS.keys()) + RESERVED_KEYS
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # get on reserved fields
    for reserved_key in reserved:
        keys = [reserved_key]
        if reserved_key != "onyo.path.absolute":
            keys.append("onyo.path.absolute")
        # verify that the key is in the header
        onyo_get(inventory, keys=keys)
        assert reserved_key in capsys.readouterr().out
        # verify asset is returned
        onyo_get(inventory, keys=keys, machine_readable=True)
        assert str(asset_path) in capsys.readouterr().out


@pytest.mark.ui({'yes': True})
def test_onyo_get_name_keys(inventory: Inventory,
                            capsys) -> None:
    r"""Print asset-name keys by default."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    name_keys = ["type", "make", "model.name", "serial"]

    # call `onyo_get()` without keys specified
    onyo_get(inventory,
             include=[asset_path])

    # verify output
    output = capsys.readouterr().out
    for name_key in name_keys:
        assert name_key in output
    # We can't easily test the asset path showing up w/o the machine_readable flag,
    # because of wrapping in the generated table. The path may have a line break plus
    # indentation within. Hence, test the column headers in the table output, but the
    # correct asset path in machine readable output:
    onyo_get(inventory,
             include=[asset_path],
             machine_readable=True)
    output = capsys.readouterr().out
    assert asset_path.name in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_errors_before_get(inventory: Inventory) -> None:
    r"""Raise the correct error if one of the specified paths is not valid."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    non_existing_asset_path = inventory.root / "non-existing" / "TYPE_MAKER_MODEL.SERIAL"

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_get,
                  inventory,
                  include=[asset_path,
                           non_existing_asset_path])


@pytest.mark.ui({'yes': True})
def test_onyo_get_simple(inventory: Inventory,
                         capsys) -> None:
    r"""Get a value in an asset."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    get_key = "some_key"

    # get a value in an asset
    onyo_get(inventory,
             include=[asset_path],
             keys=[get_key, "onyo.path.relative"])

    # verify output
    output = capsys.readouterr().out
    assert asset_path.name in output
    assert get_key in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_machine_readable(inventory: Inventory,
                                   capsys) -> None:
    r"""Get machine readable output."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    get_key = "some_key"

    # call `onyo_get()` without machine readable mode
    onyo_get(inventory,
             include=[asset_path],
             keys=[get_key, "onyo.path.relative"])

    standard_output = capsys.readouterr().out

    # call `onyo_get()` in machine readable mode
    onyo_get(inventory,
             include=[asset_path],
             keys=[get_key, "onyo.path.relative"],
             machine_readable=True)

    # verify output contains the correct information but is different from normal mode
    machine_readable_output = capsys.readouterr().out
    assert machine_readable_output != standard_output
    assert asset_path.name in machine_readable_output
    # machine_readable does not print headers, just the values
    assert "some_value" in machine_readable_output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_sorting(inventory: Inventory,
                          capsys) -> None:
    r"""Sort the output, and error on illegal sorting type."""

    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    get_key = "some_key"

    # call `onyo_get()` with sort=ascending
    onyo_get(inventory,
             sort={get_key: "ascending", "onyo.path.relative": "ascending"},
             keys=[get_key, "onyo.path.relative"])
    ascending_output = capsys.readouterr().out

    # call `onyo_get()` with sort=descending
    onyo_get(inventory,
             sort={get_key: "descending", "onyo.path.relative": "descending"},
             keys=[get_key, "onyo.path.relative"])
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
                  sort={get_key: "ILLEGAL"},
                  keys=[get_key, "onyo.path.relative"])


@pytest.mark.ui({'yes': True})
def test_onyo_get_on_directory(inventory: Inventory,
                               capsys) -> None:
    r"""Get a value from assets inside a directory."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / "somewhere"
    get_key = "some_key"

    # call `onyo_get()` on a directory
    onyo_get(inventory,
             include=[dir_path],
             keys=[get_key, "onyo.path.relative"])

    # verify output contains the asset inside the directory
    output = capsys.readouterr().out
    assert asset_path.name in output
    assert get_key in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_match(inventory: Inventory,
                        capsys) -> None:
    r"""List only only matching assets."""

    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    matches = [Filter("other=1").match]
    get_key = "some_key"

    # both assets have `get_key`, but just one asset matches
    assert get_key in inventory.repo.get_asset_content(asset_path1).keys()
    assert get_key in inventory.repo.get_asset_content(asset_path2).keys()

    # get a value just in the matching asset, but specify both paths
    onyo_get(inventory,
             include=[asset_path1, asset_path2],
             match=matches,  # pyre-ignore[6]
             keys=[get_key, "onyo.path.relative"])

    # verify output contains just information for matching assets
    output = capsys.readouterr().out
    assert asset_path1.name in output
    assert output.count(get_key) == 1
    assert asset_path2.name not in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n name: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_no_matches(inventory: Inventory,
                             capsys) -> None:
    r"""Get a list with no matching assets."""

    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    matches = [Filter("unfound=values").match]

    # `onyo_get()` is called, but no assets match
    onyo_get(inventory,
             match=matches)  # pyre-ignore[6]

    # verify output contains no assets because nothing matched
    output = capsys.readouterr().out
    assert "No inventory items matching the filter(s) were found" in output
    assert asset_path1.name not in output
    assert asset_path2.name not in output
    assert "onyo.path.relative" not in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_multiple(inventory: Inventory,
                           capsys) -> None:
    r"""Get multiple assets in a single call."""

    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"
    get_key = "some_key"

    # get a value in multiple assets at once
    onyo_get(inventory,
             include=[asset_path1,
                      asset_path2],
             keys=[get_key, "onyo.path.relative"])

    # verify output contains all assets and "onyo.path.relative" as default key
    output = capsys.readouterr().out
    assert asset_path1.name in output
    assert asset_path2.name in output
    assert "onyo.path.relative" in output
    assert get_key in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_limited(inventory: Inventory,
                          capsys) -> None:
    r"""Limit with --exclude and --depth."""

    asset_path1 = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset_path2 = inventory.root / "one_that_exists.test"

    # get a value using depth
    onyo_get(inventory,
             include=[inventory.root],
             depth=1)

    # verify output contains all assets and "onyo.path.relative" as default key
    output = capsys.readouterr().out
    assert asset_path1.name not in output
    assert asset_path2.name in output
    assert "onyo.path.relative" in output

    # exclude subtree rather than limiting depth
    onyo_get(inventory,
             exclude=asset_path1.parent)
    # verify output contains all assets and "onyo.path.relative" as default key
    output = capsys.readouterr().out
    assert asset_path1.name not in output
    assert asset_path2.name in output
    assert "onyo.path.relative" in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test\nsome_key: value"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_depth_zero(inventory: Inventory,
                             capsys) -> None:
    r"""``depth=0`` selects all assets from all subpaths."""

    onyo_get(inventory,
             include=[inventory.root],
             depth=0,
             machine_readable=True)

    # verify output contains all assets and "onyo.path.relative" as default key
    output = capsys.readouterr().out
    for asset in inventory.repo.asset_paths:
        assert asset.name in output


@pytest.mark.repo_contents(
    ["one_that_exists.test", "type: one\nmake: that\nmodel:\n  name: exists\nserial: test"])
@pytest.mark.ui({'yes': True})
def test_onyo_get_default_inventory_root(inventory: Inventory,
                                         capsys) -> None:
    r"""Empty ``include`` uses ``inventory.root`` as default."""

    onyo_get(inventory, machine_readable=True)

    # verify output contains all assets and "onyo.path.relative" as default key
    output = capsys.readouterr().out
    for asset in inventory.repo.asset_paths:
        assert asset.name in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_allows_duplicates(inventory: Inventory,
                                    capsys) -> None:
    r"""The same asset twice in ``include`` will produce it only once."""

    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"

    # call `onyo_get()` with `include` containing duplicates
    onyo_get(inventory,
             include=[asset_path, asset_path, asset_path],
             machine_readable=True)

    # verify output contains all assets and "onyo.path.relative" as default key
    output = capsys.readouterr().out
    assert output.count(asset_path.name) == 1


def test_onyo_get_asset_dir(inventory: Inventory,
                            capsys) -> None:
    r"""Get keys from an asset directory."""

    asset = Item(some_key="some_value",
                 type="TYPE",
                 make="MAKER",
                 model=dict(name="MODEL"),
                 serial="SERIAL2",
                 other=1,
                 directory=inventory.root)
    asset['onyo.is.directory'] = True
    inventory.add_asset(asset)
    asset_dir = inventory.root / "TYPE_MAKER_MODEL.SERIAL2"
    inventory.commit("add an asset dir")
    onyo_get(inventory,
             match=[Filter("other=1").match],  # pyre-ignore[6]
             keys=["onyo.path.relative", "onyo.is.directory"])
    output = capsys.readouterr().out
    assert str(asset_dir.relative_to(inventory.root)) in output
    assert str(True) in output


def test_onyo_get_is_asset_dir(inventory: Inventory,
                               capsys) -> None:
    onyo_get(inventory, keys=["onyo.path.relative", "onyo.is.directory"])
    assert str(False) in capsys.readouterr().out


@pytest.mark.ui({'yes': True})
def test_onyo_get_type_matching(inventory: Inventory,
                                capsys) -> None:
    r"""Match variable type (e.g. dict)."""

    inventory.add_asset(Item(some_key=dict(),
                             type="TYPE",
                             make="MAKE",
                             model=dict(name="MODEL"),
                             serial="SERIAL1",
                             subdict=dict(),
                             directory=inventory.root)
                        )
    inventory.add_asset(Item(some_key=dict(some="value"),
                             type="TYPE",
                             make="MAKE",
                             model=dict(name="MODEL"),
                             serial="SERIAL2",
                             directory=inventory.root)
                        )
    inventory.commit("Add assets w/ dicts")
    asset1_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL1"
    asset2_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL2"
    matches = [Filter("some_key=<dict>").match]
    onyo_get(inventory,
             include=[inventory.root],
             match=matches,  # pyre-ignore[6]
             keys=["onyo.path.relative"])

    # verify output contains matching asset
    output = capsys.readouterr().out
    assert asset1_path.name in output
    assert asset2_path.name in output

    # non-matching type filter:
    matches = [Filter("model=<list>").match]
    onyo_get(inventory,
             include=[inventory.root],
             match=matches,  # pyre-ignore[6]
             keys=["onyo.path.relative"])
    # verify output does not contain the previously matching asset
    output = capsys.readouterr().out
    assert asset1_path.name not in output
    assert asset2_path.name not in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_match_empty_dict(inventory: Inventory,
                                   capsys) -> None:
    r"""Match an empty dict (e.g. ``{}``)."""

    inventory.add_asset(Item(some_key=dict(),
                             type="TYPE",
                             make="MAKER",
                             model=dict(name="MODEL"),
                             serial="SERIAL2",
                             directory=inventory.root)
                        )
    inventory.add_asset(Item(some_key=dict(notempty="some"),
                             type="TYPE",
                             make="MAKER",
                             model=dict(name="MODEL"),
                             serial="SERIAL3",
                             directory=inventory.root)
                        )
    inventory.commit("test assets w/ dicts and lists")

    onyo_get(inventory,
             match=[Filter("some_key={}").match],  # pyre-ignore[6]
             keys=["onyo.path.relative", "some_key"])
    output = capsys.readouterr().out
    assert "SERIAL2" in output
    assert "SERIAL3" not in output

    assert "<unset>" not in output
    assert "<dict>" in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_match_empty_list(inventory: Inventory,
                                   capsys) -> None:
    r"""Match an empty list (e.g. ``[]``)."""

    inventory.add_asset(Item({"some_key": list(),
                              "type": "TYPE",
                              "make": "MAKER",
                              "model": dict(name="MODEL"),
                              "serial": "SERIAL2",
                              "directory": inventory.root,
                              "onyo.is.directory": True})
                        )
    inventory.add_asset(Item({"some_key": [1, 2],
                              "type": "TYPE",
                              "make": "MAKER",
                              "model": dict(name="MODEL"),
                              "serial": "SERIAL3",
                              "directory": inventory.root,
                              "onyo.is.directory": True})
                        )
    inventory.commit("test assets w/ dicts and lists")

    onyo_get(inventory,
             match=[Filter("some_key=[]").match],  # pyre-ignore[6]
             keys=["onyo.path.relative", "some_key"])
    output = capsys.readouterr().out
    assert "SERIAL2" in output
    assert "SERIAL3" not in output

    assert "<unset>" not in output
    assert "<list>" in output


@pytest.mark.ui({'yes': True})
def test_onyo_get_unset_values(inventory: Inventory,
                               capsys) -> None:
    """Unset keys and values return as ``<unset>``."""

    asset = Item(type="TYPE",
                 make="MAKE",
                 model=dict(name="MODEL"),
                 serial="SERIAL2",
                 directory=inventory.root)
    test_pairs = dict(novalue=None,
                      emptystring="")
    asset.update(**test_pairs)
    inventory.add_asset(asset)
    inventory.commit("add asset w/ empty values")
    asset1_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    asset2_path = inventory.root / "TYPE_MAKE_MODEL.SERIAL2"

    onyo_get(inventory,
             keys=["onyo.path.relative", "novalue", "emptystring"],
             machine_readable=True)
    output = capsys.readouterr().out

    # asset1 is brought in by fixture and doesn't have the keys we print,
    # asset2 has those keys, but they have values that are supposed to be UNSET_VALUE.
    expected_lines = [f"{str(p.relative_to(inventory.root))}\t{UNSET_VALUE}\t{UNSET_VALUE}"
                      for p in [asset1_path, asset2_path]]
    assert expected_lines[0] in output.splitlines()
    assert expected_lines[1] in output.splitlines()


@pytest.mark.ui({'yes': True})
def test_onyo_get_items(inventory: Inventory, capsys) -> None:
    """Get directories and templates."""

    onyo_get(inventory,
             keys=["onyo.path.relative"],
             include=[inventory.repo.template_dir],
             machine_readable=True)
    output = capsys.readouterr().out
    assert len(output.splitlines()) == 2
    assert str(TEMPLATE_DIR / "empty") in output
    assert str(TEMPLATE_DIR / "laptop.example") in output

    onyo_get(inventory,
             keys=["onyo.path.relative"],
             machine_readable=True,
             include=[inventory.root / "somewhere"],
             types=['directories'])
    output_lines = capsys.readouterr().out.splitlines(keepends=True)
    assert len(output_lines) == 2
    assert "somewhere\n" in output_lines
    assert "somewhere/nested\n" in output_lines
