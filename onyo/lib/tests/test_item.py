from __future__ import annotations

from pathlib import Path
from types import NoneType

import pytest

from onyo.lib.consts import ANCHOR_FILE_NAME
from onyo.lib.items import Item
from onyo.lib.pseudokeys import (
    PSEUDO_KEYS,
    PSEUDOKEY_ALIASES,
)

asset_dict = Item({
    "type": "atype",
    "make": "amake",
    "model": {"name": "amodel"},
    "serial": "001",
    "path": Path("subdir") / "atype_amake_amodel.1"
}
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


@pytest.mark.inventory_assets(asset_dict)
def test_item_init(onyorepo) -> None:
    # TODO: Values may need to change. Stringification!
    #       But may be not for pseudo-keys? There are never written out.
    #       However, they are meant to be specifiable in a (template-) YAML.
    constructor_calls = [Item(),
                         Item({'some': {'nested': '0_03'}}),
                         Item(some={'nested': '0_03'}),
                         Item(onyorepo.test_annotation['dirs'][0]),
                         Item(onyorepo.test_annotation['dirs'][0], onyorepo),
                         Item(onyorepo.test_annotation['assets'][0]['onyo.path.absolute'], onyorepo),
                         Item(onyorepo.test_annotation['templates'][0], onyorepo),
                         ]

    for item, idx in zip(constructor_calls, range(len(constructor_calls))):
        # All pseudo-keys are accessible:
        assert all(pk in item for pk in PSEUDO_KEYS)
        # Given key-value pairs are accessible:
        assert (item.get('some.nested') == '0_03') if idx in [1, 2] else item.get('some.nested') is None
        # Non-existing keys raise proper error:
        pytest.raises(KeyError, lambda: item['doesnotexist'])
        # however get() does not raise for non-existing keys
        for key in ['dne', 'type.dne', 'model.dne', 'path.dne', 'dne.dne']:
            assert item.get(key) is None
        # If a Path was given, at the very least the absolute path is available:
        if idx in [3, 4, 5, 6]:
            assert isinstance(item.get('onyo.path.absolute'), Path)
            assert item.get('onyo.path.name') == item['onyo.path.absolute'].name
        else:
            # otherwise, this is unset
            assert item.get('onyo.path.absolute') is None
        # If the repo was given, relative-to-root paths are available as well:
        if idx in [4, 5, 6]:
            assert isinstance(item.get('onyo.path.relative'), Path)
            assert isinstance(item.get('onyo.path.parent'), Path)
        else:
            # otherwise, relative-to-root paths are unset
            assert item.get('onyo.path.relative') is None
            assert item.get('onyo.path.parent') is None
        # Check actual paths:
        if idx == 4:
            # item is a dir in a repo
            assert item.get('onyo.path.absolute') == onyorepo.test_annotation['dirs'][0]
            assert item.get('onyo.path.relative') == onyorepo.test_annotation['dirs'][0].relative_to(onyorepo.git.root)
            assert item.get('onyo.path.parent') == onyorepo.test_annotation['dirs'][0].parent.relative_to(onyorepo.git.root)
            assert item.get('onyo.path.file') == onyorepo.test_annotation['dirs'][0].relative_to(onyorepo.git.root) / ANCHOR_FILE_NAME
            assert item.get('onyo.is.empty') is not None
        elif idx == 5:
            assert item.get('onyo.path.absolute') == onyorepo.test_annotation['assets'][0]['onyo.path.absolute']
            assert item.get('onyo.path.relative') == onyorepo.test_annotation['assets'][0]['onyo.path.absolute'].relative_to(onyorepo.git.root)
            assert item.get('onyo.path.parent') == onyorepo.test_annotation['assets'][0]['onyo.path.absolute'].parent.relative_to(onyorepo.git.root)
            assert item.get('onyo.path.file') == item.get('onyo.path.relative')
            assert item['onyo.is.empty'] is None
        elif idx == 6:
            assert item.get('onyo.path.absolute') == onyorepo.test_annotation['templates'][0]
            assert item.get('onyo.path.relative') == onyorepo.test_annotation['templates'][0].relative_to(onyorepo.git.root)
            assert item.get('onyo.path.parent') == onyorepo.test_annotation['templates'][0].parent.relative_to(onyorepo.git.root)
            assert item.get('onyo.path.file') == item.get('onyo.path.relative')
            assert item['onyo.is.empty'] is None
        if item.repo is None:
            assert item['onyo.is.asset'] is None
            assert item['onyo.is.directory'] is None
            assert item['onyo.is.template'] is None
            assert item['onyo.is.empty'] is None
        else:
            assert item['onyo.is.asset'] is (
                item['onyo.path.absolute'] in [a['onyo.path.absolute'] for a in (onyorepo.test_annotation['assets'])]) or \
                item['onyo.path.absolute'] in onyorepo.test_annotation['templates']
            assert item['onyo.is.directory'] is (item['onyo.path.absolute'] in onyorepo.test_annotation['dirs'])
            assert item['onyo.is.template'] is (onyorepo.template_dir in item['onyo.path.absolute'].parents)

        # Aliases
        for k in PSEUDOKEY_ALIASES:
            assert item[k] == item[PSEUDOKEY_ALIASES[k]]

        # content is read from file:
        if idx in [5, 6]:
            assert all(k in item.keys() for k in ['type', 'make', 'model.name'])


def test_item_init_path(tmp_path) -> None:
    r"""Load an Item from a YAML file."""

    asset_path = tmp_path / "asset-file"
    asset_path.write_text(asset_file_content)

    item = Item(asset_path)
    assert isinstance(item, Item)

    def assert_all_keys_strings(d: Item) -> None:
        for key in d.keys():
            assert isinstance(key, str)
            if isinstance(d[key], list):
                # This does not yet consider lists/dicts within lists!
                assert all(isinstance(i, str) for i in d[key])
                continue
            if isinstance(d[key], dict):
                assert_all_keys_strings(d[key])
                continue

            match key:
                # pseudokeys
                case k if k.startswith('onyo.is.'):
                    assert isinstance(d[key], (bool, NoneType))
                case 'onyo.path.name':
                    assert isinstance(d[key], str)
                case k if k.startswith('onyo.path.'):
                    assert isinstance(d[key], (Path, NoneType))
                case k if k.startswith('onyo.was.'):
                    assert isinstance(d[key], (bool, str, NoneType))
                # content
                case k if 'null' in k:
                    assert d[key] is None
                case 'model.explicit':
                    assert isinstance(d[key], int)
                case '003_5'|'a_false':
                    assert isinstance(d[key], bool)
                case _:
                    if d[key] is None:
                        assert key == 'sdafdfasdfasd'
                    assert isinstance(d[key], str)

    assert_all_keys_strings(item)


def test_item_yaml_no_pseudokeys(tmp_path) -> None:
    """Pseudokeys are not included in the YAML output."""

    asset_path = tmp_path / "asset-file"
    asset_path.write_text(asset_file_content)

    item = Item(asset_path)
    item['onyo.test-pseudokey'] = 'should not be in YAML output'

    output_yaml = item.yaml()
    assert 'test-pseudokey' not in output_yaml
    assert 'should not be in YAML output' not in output_yaml


def test_item_roundtrip(tmp_path) -> None:
    """Content roundtrips correctly.

    Path -> Item(Path) -> Item.yaml().
    """

    asset_path = tmp_path / "asset-file"
    asset_path.write_text(asset_file_content)

    item = Item(asset_path)

    # TODO: hack
    # ruamel does not roundtrip the various representations of Null. And
    # replaces them with the empty form.
    fixed_content = asset_file_content.replace("~", " ")  # Space, b/c the comment position is retained.
    fixed_content = fixed_content.replace(" Null", "").replace(" NULL", "").replace(" null", "")

    assert item.yaml() == fixed_content
