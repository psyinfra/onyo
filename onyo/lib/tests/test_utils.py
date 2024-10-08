import os

import pytest
from ruamel.yaml import YAML  # pyre-ignore[21]

from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.utils import dict_to_asset_yaml


def test_dict_to_asset_yaml() -> None:
    r"""Test Dict, CommentedMap, and empty dict."""
    # normal python dict
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': 8675309}
    d_expected_output = f"---{os.linesep}type: TYPE{os.linesep}make: MAKE{os.linesep}model: MODEL{os.linesep}serial: 8675309{os.linesep}"
    assert d_expected_output == dict_to_asset_yaml(d)

    # YAML with comments
    yaml_string = f"---{os.linesep}" + \
                  f"model: MODEL{os.linesep}" + \
                  f"# You can be my Yoko Onyo{os.linesep}" + \
                  f"make: MAKE{os.linesep}" + \
                  f"type: TYPE{os.linesep}" + \
                  f"# service tag for Dell{os.linesep}" + \
                  f"serial: SERIAL{os.linesep}"
    yaml = YAML(typ='rt', pure=True)
    yaml_dict_w_comments = yaml.load(yaml_string)
    assert yaml_string == dict_to_asset_yaml(yaml_dict_w_comments)

    # empty top-level dict should be stripped
    empty = {}
    empty_expected_output = f"---{os.linesep}"
    assert empty_expected_output == dict_to_asset_yaml(empty)

    # empty nested dict should be retained
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': 8675309, 'dict': {}}
    d_expected_output = f"---{os.linesep}type: TYPE{os.linesep}make: MAKE{os.linesep}model: MODEL{os.linesep}serial: 8675309{os.linesep}dict: {{}}{os.linesep}"
    assert d_expected_output == dict_to_asset_yaml(d)


@pytest.mark.parametrize('rkey', PSEUDO_KEYS + RESERVED_KEYS)
def test_redaction_dict_to_asset_yaml(rkey: str) -> None:
    r"""Reserved- and Pseudo-Keys should not be serialized."""
    d = {'type': 'TYPE', 'make': 'MAKE', 'model': 'MODEL', 'serial': 8675309, rkey: 'REDACT_ME'}
    d_expected_output = f"---{os.linesep}type: TYPE{os.linesep}make: MAKE{os.linesep}model: MODEL{os.linesep}serial: 8675309{os.linesep}"
    assert d_expected_output == dict_to_asset_yaml(d)
