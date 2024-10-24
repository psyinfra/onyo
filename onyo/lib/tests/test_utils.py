import pytest
from ruamel.yaml import YAML  # pyre-ignore[21]

from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.utils import dict_to_asset_yaml


def test_dict_to_asset_yaml() -> None:
    r"""Test Dict, CommentedMap, and empty dict."""
    # normal python dict
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': 8675309}
    d_expected_output = "---\ntype: TYPE\nmake: MAKE\nmodel: MODEL\nserial: 8675309\n"
    assert d_expected_output == dict_to_asset_yaml(d)

    # YAML with comments
    yaml_string = "---\n" + \
                  "model: MODEL\n" + \
                  "# You can be my Yoko Onyo\n" + \
                  "make: MAKE\n" + \
                  "type: TYPE\n" + \
                  "# service tag for Dell\n" + \
                  "serial: SERIAL\n"
    yaml = YAML(typ='rt', pure=True)
    yaml_dict_w_comments = yaml.load(yaml_string)
    assert yaml_string == dict_to_asset_yaml(yaml_dict_w_comments)

    # empty top-level dict should be stripped
    empty = {}
    empty_expected_output = "---\n"
    assert empty_expected_output == dict_to_asset_yaml(empty)

    # empty nested dict should be retained
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': 8675309, 'dict': {}}
    d_expected_output = "---\ntype: TYPE\nmake: MAKE\nmodel: MODEL\nserial: 8675309\ndict: {}\n"
    assert d_expected_output == dict_to_asset_yaml(d)


@pytest.mark.parametrize('rkey', PSEUDO_KEYS + RESERVED_KEYS)
def test_redaction_dict_to_asset_yaml(rkey: str) -> None:
    r"""Reserved- and Pseudo-Keys should not be serialized."""
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': 8675309, rkey: 'REDACT_ME'}
    d_expected_output = "---\ntype: TYPE\nmake: MAKE\nmodel: MODEL\nserial: 8675309\n"
    assert d_expected_output == dict_to_asset_yaml(d)
