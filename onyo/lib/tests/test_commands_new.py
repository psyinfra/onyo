import os

import pytest
import subprocess
from pathlib import Path

from ..commands import onyo_new
import onyo
from onyo.lib.onyo import OnyoRepo
from onyo.lib.inventory import Inventory


# TODO: Derive path from installed package resources (and don't place it within a specific test location):
prepared_tsvs = [p for p in (Path(onyo.__file__).parent / "commands" / "tests" / "tables").iterdir()]


# TODO: Asset dirs!
# TODO: Commit message!
# TODO: Changed name scheme config


def test_onyo_new_invalid(inventory: Inventory) -> None:
    # no arguments is insufficient
    pytest.raises(ValueError, onyo_new, inventory)
    # empty `keys` is not good enough either
    pytest.raises(ValueError, onyo_new, inventory, keys=[])
    # edit should fail in non-interactive test
    pytest.raises(subprocess.CalledProcessError, onyo_new, inventory, edit=True)
    # tsv must exist:
    pytest.raises(FileNotFoundError, onyo_new, inventory, tsv=inventory.root / "nonexisting.tsv")


@pytest.mark.ui({'yes': True})
@pytest.mark.parametrize('tsv', prepared_tsvs)
def test_onyo_new_tsv(inventory: Inventory, tsv: Path) -> None:
    if tsv.name.startswith('error'):
        # TODO: Be more specific about the errors
        pytest.raises(ValueError, onyo_new, inventory, tsv)
    else:
        # TODO: Same here; just ensures those tables still don't crash
        onyo_new(inventory, tsv=tsv)
        inventory.repo.git._git(['reset', '--hard', 'HEAD~1'])


@pytest.mark.ui({'yes': True})
def test_onyo_new_keys(inventory: Inventory) -> None:
    specs = [{'type': 'a type',
              'make': 'I made it',
              'model': 'a model',
              'serial': '002'},
             {'type': 'a type',
              'make': 'I made it',
              'model': 'a model',
              'serial': '003'}]
    onyo_new(inventory,
             path=inventory.root / "empty",
             keys=specs)
    for s in specs:
        p = inventory.root / "empty" / f"{s['type']}_{s['make']}_{s['model']}.{s['serial']}"
        assert inventory.repo.is_asset_path(p)
        assert p not in inventory.repo.git.files_untracked
        new_asset = inventory.get_asset(p)
        assert new_asset.get("path") == p
        assert all(new_asset[k] == s[k] for k in s.keys())

    # faux serial and 'directory' key
    specs = [{'type': 'A',
              'make': 'faux',
              'model': 'serial',
              'directory': 'brandnew',
              'serial': 'faux'},
             {'type': 'Another',
              'make': 'faux',
              'model': 'serial',
              'directory': 'completely/elsewhere',
              'serial': 'faux'}]
    # 'directory' is in conflict with `path` being given:
    pytest.raises(ValueError,
                  onyo_new,
                  inventory,
                  path=inventory.root / "empty",
                  keys=specs)
    # w/o `path` everything is fine:
    onyo_new(inventory, keys=specs)

    for s in specs:
        files = [p
                 for p in (inventory.root / f"{s['directory']}").iterdir()
                 if p.name != OnyoRepo.ANCHOR_FILE
                 ]
        assert len(files) == 1
        # expected filename (except serial):
        assert files[0].name.startswith(f"{s['type']}_{s['make']}_{s['model']}.")
        assert inventory.repo.is_asset_path(files[0])
        assert files[0] not in inventory.repo.git.files_untracked
        new_asset = inventory.get_asset(files[0])
        assert new_asset.get("path") == files[0]
        # reserved key 'directory' is not part of the asset's content
        assert 'directory' not in new_asset.keys()
        # content equals spec:
        assert all(new_asset[k] == s[k]
                   for k in s.keys()
                   if k not in ['directory', 'serial'])

    # missing required field:
    specs = [{'somekey': 'somevalue'}]
    pytest.raises(ValueError, onyo_new, inventory, keys=specs)

    # use templates and `path`'s default - CWD.
    # Attention: CWD being inventory.root relies on current implementation of
    # the repo fixture, which the inventory fixture builds upon.
    specs = [{'type': 'flavor',
              'make': 'manufacturer',
              'model': 'exquisite',
              'template': 'laptop.example',
              'serial': '1234'}]
    onyo_new(inventory, keys=specs)
    expected_path = inventory.root / f"{specs[0]['type']}_{specs[0]['make']}_{specs[0]['model']}.{specs[0]['serial']}"
    assert inventory.repo.is_asset_path(expected_path)
    asset_content = inventory.repo.get_asset_content(expected_path)
    # check for template keys:
    # (Note: key must be there - no `KeyError`; but content is `None`)
    for k in ['RAM', 'Size', 'USB']:
        assert asset_content[k] is None


@pytest.mark.ui({'yes': True})
def test_onyo_new_edit(inventory: Inventory, monkeypatch) -> None:

    directory = inventory.root / "edited"
    monkeypatch.setenv('EDITOR', "printf 'key: value' >>")

    specs = [{'template': 'empty',
              'model': 'MODEL',
              'make': 'MAKER',
              'type': 'TYPE',
              'serial': 'totally_random'}]
    onyo_new(inventory, keys=specs, path=directory, edit=True)
    expected_path = directory / "TYPE_MAKER_MODEL.totally_random"
    assert inventory.repo.is_asset_path(expected_path)
    assert expected_path not in inventory.repo.git.files_untracked
    asset_content = inventory.repo.get_asset_content(expected_path)
    assert asset_content['key'] == 'value'

    # missing required fields:
    specs = [{'template': 'empty'}]

    # Note, that when starting from an empty template, appending a
    # "key: value" to the file doesn't work, b/c the empty YAML
    # document is "{}" not "". Hence, appending would lead to a
    # YAML parser error.
    monkeypatch.setenv('EDITOR', "printf 'key: value' >")
    pytest.raises(ValueError, onyo_new, inventory, keys=specs, path=directory, edit=True)

    # file already exists:
    edit_str = f"model: MODEL{os.linesep}make: MAKER{os.linesep}type: TYPE{os.linesep}"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty',
              'serial': 'totally_random'}]

    pytest.raises(ValueError, onyo_new, inventory, keys=specs, path=directory, edit=True)

    # asset already exists (but elsewhere - see fixture):
    edit_str = f"model: MODEL{os.linesep}make: MAKER{os.linesep}type: TYPE{os.linesep}serial: SERIAL{os.linesep}"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty'}]
    pytest.raises(ValueError, onyo_new, inventory, keys=specs, path=directory, edit=True)
