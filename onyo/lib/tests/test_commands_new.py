import os
import subprocess
from pathlib import Path

import pytest

import onyo
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from ..commands import onyo_new

# TODO: Derive path from installed package resources (and don't place it within a specific test location):
prepared_tsvs = [p for p in (Path(onyo.__file__).parent / "cli" / "tests" / "tables").iterdir()]


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
    # clone and template are mutually exclusive
    pytest.raises(ValueError, onyo_new, inventory,
                  keys=[{'serial': 'faux'}],
                  clone=inventory.root / "somewhere" / "nested" / "TYPE_MAKE_MODEL.SERIAL",
                  template='laptop.example')
    assert inventory.repo.git.is_clean_worktree()


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
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_keys(inventory: Inventory) -> None:
    """`onyo_new()` must create new assets with the contents set correctly
    when called with `keys`.

    Each successful call of `onyo_new()` must add one commit.
    """
    specs = [{'type': 'a type',
              'make': 'I made it',
              'model': 'a model',
              'serial': '002'},
             {'type': 'a type',
              'make': 'I made it',
              'model': 'a model',
              'serial': '003'}]
    old_hexsha = inventory.repo.git.get_hexsha()
    onyo_new(inventory,
             directory=inventory.root / "empty",
             keys=specs)  # pyre-ignore[6] How is that not fitting `List[Dict[str, int | float | str]]`?
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha

    for s in specs:
        p = inventory.root / "empty" / f"{s['type']}_{s['make']}_{s['model']}.{s['serial']}"
        assert inventory.repo.is_asset_path(p)
        assert p in inventory.repo.git.files
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
    # 'directory' is in conflict with `directory` being given:
    pytest.raises(ValueError,
                  onyo_new,
                  inventory,
                  directory=inventory.root / "empty",
                  keys=specs)
    # w/o `directory` everything is fine:
    onyo_new(inventory,
             keys=specs)  # pyre-ignore[6] How is that not fitting `List[Dict[str, int | float | str]]`?
    # another commit added
    assert inventory.repo.git.get_hexsha('HEAD~2') == old_hexsha

    for s in specs:
        files = [p
                 for p in (inventory.root / f"{s['directory']}").iterdir()
                 if p.name != OnyoRepo.ANCHOR_FILE_NAME
                 ]
        assert len(files) == 1
        # expected filename (except serial):
        assert files[0].name.startswith(f"{s['type']}_{s['make']}_{s['model']}.")
        assert inventory.repo.is_asset_path(files[0])
        assert files[0] in inventory.repo.git.files
        new_asset = inventory.get_asset(files[0])
        assert new_asset.get("path") == files[0]
        assert new_asset.get("directory") == files[0].parent
        # content equals spec:
        assert all(new_asset[k] == s[k]
                   for k in s.keys()
                   if k not in ['directory', 'serial'])

    # missing required field:
    specs = [{'somekey': 'somevalue'}]
    pytest.raises(ValueError, onyo_new, inventory, keys=specs)

    # use templates and `directory`'s default - CWD.
    # Attention: CWD being inventory.root relies on current implementation of
    # the repo fixture, which the inventory fixture builds upon.
    specs = [{'type': 'flavor',
              'make': 'manufacturer',
              'model': 'exquisite',
              'template': 'laptop.example',
              'serial': '1234'}]
    onyo_new(inventory,
             keys=specs)  # pyre-ignore[6] How is that not fitting `List[Dict[str, int | float | str]]`?
    # another commit added
    assert inventory.repo.git.get_hexsha('HEAD~3') == old_hexsha
    expected_path = inventory.root / f"{specs[0]['type']}_{specs[0]['make']}_{specs[0]['model']}.{specs[0]['serial']}"
    assert inventory.repo.is_asset_path(expected_path)
    assert expected_path in inventory.repo.git.files
    asset_content = inventory.repo.get_asset_content(expected_path)
    # check for template keys:
    # (Note: key must be there - no `KeyError`; but content is `None`)
    for k in ['RAM', 'Size', 'USB']:
        assert asset_content[k] is None
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_creates_directories(inventory: Inventory) -> None:
    """`onyo_new()` must create new directories and subdirectories when called
    on a `directory` that does not yet exist, and add assets correctly to it.
    """
    specs = [{'type': 'a type',
              'make': 'I made it',
              'model': 'a model',
              'serial': '002'},
             {'type': 'a type',
              'make': 'I made it',
              'model': 'a model',
              'serial': '003'}]
    new_directory = inventory.root / "does" / "not" / "yet" / "exist"
    old_hexsha = inventory.repo.git.get_hexsha()

    onyo_new(inventory,
             directory=new_directory,
             keys=specs)  # pyre-ignore[6] How is that not fitting `List[Dict[str, int | float | str]]`?

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha

    # the new directories exist
    assert new_directory.is_dir()
    assert (new_directory / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    assert (inventory.root / "does" / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files

    # new assets are added
    for s in specs:
        p = new_directory / f"{s['type']}_{s['make']}_{s['model']}.{s['serial']}"
        assert inventory.repo.is_asset_path(p)
        assert p in inventory.repo.git.files
        new_asset = inventory.get_asset(p)
        assert new_asset.get("path") == p
        assert all(new_asset[k] == s[k] for k in s.keys())
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_edit(inventory: Inventory, monkeypatch) -> None:
    directory = inventory.root / "edited"
    monkeypatch.setenv('EDITOR', "printf 'key: value' >>")

    specs = [{'template': 'empty',
              'model': 'MODEL',
              'make': 'MAKER',
              'type': 'TYPE',
              'serial': 'totally_random'}]
    onyo_new(inventory,
             keys=specs,  # pyre-ignore[6] How is that not fitting `List[Dict[str, int | float | str]]`?
             directory=directory,
             edit=True)
    expected_path = directory / "TYPE_MAKER_MODEL.totally_random"
    assert inventory.repo.is_asset_path(expected_path)
    assert expected_path in inventory.repo.git.files
    asset_content = inventory.repo.get_asset_content(expected_path)
    assert asset_content['key'] == 'value'

    # missing required fields:
    specs = [{'template': 'empty'}]

    # Note, that when starting from an empty template, appending a
    # "key: value" to the file doesn't work, b/c the empty YAML
    # document is "{}" not "". Hence, appending would lead to a
    # YAML parser error.
    monkeypatch.setenv('EDITOR', "printf 'key: value' >")
    pytest.raises(ValueError, onyo_new, inventory, keys=specs, directory=directory, edit=True)

    # file already exists:
    edit_str = f"model: MODEL{os.linesep}make: MAKER{os.linesep}type: TYPE{os.linesep}"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty',
              'serial': 'totally_random'}]

    pytest.raises(ValueError, onyo_new, inventory, keys=specs, directory=directory, edit=True)

    # asset already exists (but elsewhere - see fixture):
    edit_str = f"model: MODEL{os.linesep}make: MAKER{os.linesep}type: TYPE{os.linesep}serial: SERIAL{os.linesep}"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty'}]
    pytest.raises(ValueError, onyo_new, inventory, keys=specs, directory=directory, edit=True)
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_clones(inventory: Inventory) -> None:
    existing_asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    existing_asset = inventory.get_asset(existing_asset_path)
    asset_dir = inventory.root / "somewhere"
    old_hexsha = inventory.repo.git.get_hexsha()

    onyo_new(inventory,
             keys=[{'serial': 'ANOTHER'},
                   {'serial': 'whatever'}],
             clone=existing_asset_path,
             directory=asset_dir)

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
    # left worktree clean
    assert inventory.repo.git.is_clean_worktree()

    # first new asset:
    new_asset_path1 = asset_dir / f"{existing_asset_path.name.split('.')[0]}.ANOTHER"
    assert inventory.repo.is_asset_path(new_asset_path1)
    new_asset = inventory.get_asset(new_asset_path1)
    # equals existing asset except for directory, path, and serial:
    assert all(v == new_asset[k] for k, v in existing_asset.items() if k not in ['directory', 'path', 'serial'])
    assert new_asset['serial'] == 'ANOTHER'

    # second new asset
    new_asset_path2 = asset_dir / f"{existing_asset_path.name.split('.')[0]}.whatever"
    assert inventory.repo.is_asset_path(new_asset_path2)
    new_asset = inventory.get_asset(new_asset_path2)
    # equals existing asset except for directory, path, and serial:
    assert all(v == new_asset[k] for k, v in existing_asset.items() if k not in ['directory', 'path', 'serial'])
    assert new_asset['serial'] == 'whatever'
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_asset_dir(inventory: Inventory) -> None:
    new_asset_dir = inventory.root / "a_b_c.1"
    old_hexsha = inventory.repo.git.get_hexsha()
    onyo_new(inventory,
             keys=[{"type": "a",
                    "make": "b",
                    "model": "c",
                    "serial": "1",
                    "is_asset_directory": True}])
    assert inventory.repo.is_asset_dir(new_asset_dir)
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha
