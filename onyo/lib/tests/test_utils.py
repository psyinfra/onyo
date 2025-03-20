from onyo.lib.utils import (
    get_asset_content,
    yaml_to_dict_multi,
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
a_false: false
explicit_null: null
tilde_null: ~ # what now
implicit_null:
emptystring: ''
description: |
  This is a long text
  containing multiple lines.
"""


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

        match key:
            case 'explicit':
                assert isinstance(d[key], int)
            case '003_5' | 'a_false':
                assert isinstance(d[key], bool)
            case _:
                assert isinstance(d[key], str)


def test_get_asset_content(tmp_path) -> None:
    r"""Turn YAML into a dict representation w/ correct key-stringification."""

    asset_file = tmp_path / "asset-file"
    asset_file.write_text(asset_file_content)

    asset_dict = get_asset_content(asset_file)
    assert isinstance(asset_dict, dict)  # this includes ruamel's CommentedMap

    assert_all_keys_strings(asset_dict)


def test_yaml_to_dict_multi(tmp_path) -> None:
    asset_file = tmp_path / "asset-file"
    multidoc = asset_file_content+asset_file_content
    asset_file.write_text(multidoc)

    from_file = [i for i in yaml_to_dict_multi(asset_file)]
    from_string = [i for i in yaml_to_dict_multi(multidoc)]
    assert len(from_file) == len(from_string) == 2
    assert all(isinstance(d, dict) for d in from_file)
    assert all(isinstance(d, dict) for d in from_string)
    assert from_file[0] == from_string[0]
    assert from_file[1] == from_string[1]

    for d in from_file + from_string:
        assert_all_keys_strings(d)
