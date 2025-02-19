from pathlib import Path

import pytest

from onyo.lib.onyo import OnyoRepo
from ..items import Item
from ..pseudokeys import PSEUDO_KEYS, PSEUDOKEY_ALIASES

asset_dict = Item({
    "type": "atype",
    "make": "amake",
    "model": {"name": "amodel"},
    "serial": "001",
    "path": Path("subdir") / "atype_amake_amodel.1"
}
)


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
                         Item(onyorepo.test_annotation['templates'][1], onyorepo),
                         ]

    for item, idx in zip(constructor_calls, range(len(constructor_calls))):
        # All pseudo-keys are accessible:
        assert all(pk in item for pk in PSEUDO_KEYS)
        # Given key-value pairs are accessible:
        assert (item.get('some.nested') == '0_03') if idx in [1, 2] else item.get('some.nested') is None
        # Non-existing keys raise proper error:
        pytest.raises(KeyError, lambda: item['doesnotexist'])
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
            assert item.get('onyo.path.file') == onyorepo.test_annotation['dirs'][0].relative_to(onyorepo.git.root) / OnyoRepo.ANCHOR_FILE_NAME
            assert item.get('onyo.is.empty') is not None
        elif idx == 5:
            assert item.get('onyo.path.absolute') == onyorepo.test_annotation['assets'][0]['onyo.path.absolute']
            assert item.get('onyo.path.relative') == onyorepo.test_annotation['assets'][0]['onyo.path.absolute'].relative_to(onyorepo.git.root)
            assert item.get('onyo.path.parent') == onyorepo.test_annotation['assets'][0]['onyo.path.absolute'].parent.relative_to(onyorepo.git.root)
            assert item.get('onyo.path.file') == item.get('onyo.path.relative')
            assert item['onyo.is.empty'] is None
        elif idx == 6:
            assert item.get('onyo.path.absolute') == onyorepo.test_annotation['templates'][1]
            assert item.get('onyo.path.relative') == onyorepo.test_annotation['templates'][1].relative_to(onyorepo.git.root)
            assert item.get('onyo.path.parent') == onyorepo.test_annotation['templates'][1].parent.relative_to(onyorepo.git.root)
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
            assert item['onyo.is.template'] is (onyorepo.git.root / onyorepo.TEMPLATE_DIR in item['onyo.path.absolute'].parents)

        # Aliases
        for k in PSEUDOKEY_ALIASES:
            assert item[k] == item[PSEUDOKEY_ALIASES[k]]

        # content is read from file:
        if idx in [5, 6]:
            assert all(k in item.keys() for k in ['type', 'make', 'model.name'])
