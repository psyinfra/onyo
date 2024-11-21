import pytest

from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.utils import (
    dict_to_asset_yaml,
    get_asset_content,
)

asset_file_content = """---
# top-level comment
type: a  # key comment
make: b
model:  # comment at intermediate node
  name: c # comment in nested dict-key
  # comment in nested dict
  more: d
  integer: 1
  explicit: !!int '2'
  float: 1.2
  list:
  - 1.2
  - b
  - 003_5
# keys and values need to preserve leading zeroes and underscores:
serial: 00012_3456
003_5: true
explicit_null: null
tilde_null: ~ # what now
implicit_null:
emptystring: ''
description: |
  This is a long text
  containing multiple lines.
"""


def test_dict_to_asset_yaml() -> None:
    r"""Test Dict, CommentedMap, and empty dict."""
    # normal python dict
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': '008675309', 'explicit': 123}
    d_expected_output = "---\ntype: TYPE\nmake: MAKE\nmodel: MODEL\nserial: 008675309\nexplicit: !!int '123'\n"
    assert d_expected_output == dict_to_asset_yaml(d)

    # empty top-level dict should be stripped
    empty = {}
    empty_expected_output = "---\n"
    assert empty_expected_output == dict_to_asset_yaml(empty)

    # empty nested dict should be retained
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': '008675309', 'explicit': 123, 'dict': {}}
    d_expected_output = "---\ntype: TYPE\nmake: MAKE\nmodel: MODEL\nserial: 008675309\nexplicit: !!int '123'\ndict: {}\n"
    assert d_expected_output == dict_to_asset_yaml(d)


@pytest.mark.parametrize('rkey', PSEUDO_KEYS + RESERVED_KEYS)
def test_redaction_dict_to_asset_yaml(rkey: str) -> None:
    r"""Reserved- and Pseudo-Keys should not be serialized."""
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': '008675309', 'explicit': 123, rkey: 'REDACT_ME'}
    d_expected_output = "---\ntype: TYPE\nmake: MAKE\nmodel: MODEL\nserial: 008675309\nexplicit: !!int '123'\n"
    assert d_expected_output == dict_to_asset_yaml(d)


def test_get_asset_content(tmp_path) -> None:
    r"""Turn YAML into a dict representation w/ correct key-stringification."""

    asset_file = tmp_path / "asset-file"
    asset_file.write_text(asset_file_content)

    asset_dict = get_asset_content(asset_file)
    assert isinstance(asset_dict, dict)  # this includes ruamel's CommentedMap

    def assert_all_keys_strings(d: dict) -> None:
        for key in d.keys():
            assert isinstance(key, str)
            if isinstance(d[key], list):
                # This does not yet consider lists/dicts within lists!
                assert all(isinstance(i, str) for i in d[key])
                continue
            if isinstance(d[key], dict):
                assert_all_keys_strings(d[key])
                continue
            if 'null' in key:
                assert d[key] is None
                continue
            assert isinstance(d[key], int if key == 'explicit' else str)

    assert_all_keys_strings(asset_dict)


def test_roundtrip(tmp_path) -> None:
    """Test roundtrip get_asset_content->dict_to_asset_yaml"""
    asset_file = tmp_path / "asset-file"
    asset_file.write_text(asset_file_content)

    asset_dict = get_asset_content(asset_file)
    # For now values ruamel does not roundtrip the representation. It's the `empty:` form:
    write_back = asset_file_content.replace("~", " ")  # Space, b/c the comment position is retained.
    write_back = write_back.replace(" Null", "").replace(" NULL", "").replace(" null", "")
    assert dict_to_asset_yaml(asset_dict) == write_back
