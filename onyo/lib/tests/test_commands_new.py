import subprocess

import pytest

from onyo.lib.inventory import Inventory
from onyo.lib.items import Item
from onyo.lib.onyo import OnyoRepo
from onyo.lib.utils import DotNotationWrapper
from . import check_commit_msg
from ..commands import onyo_new


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
    # clone and template are mutually exclusive
    pytest.raises(ValueError, onyo_new, inventory,
                  keys=[{'serial': 'faux'}],
                  clone=inventory.root / "somewhere" / "nested" / "TYPE_MAKE_MODEL.SERIAL",
                  template='laptop.example')
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_keys(inventory: Inventory) -> None:
    r"""`onyo_new()` must create new assets with the contents set correctly
    when called with `keys`.

    Each successful call of `onyo_new()` must add one commit.
    """
    specs = [DotNotationWrapper({'type': 'a type',
                                 'make': 'I made it',
                                 'model': {'name': 'a model'},
                                 'serial': '002'}),
             DotNotationWrapper({'type': 'a type',
                                 'make': 'I made it',
                                 'model': {'name': 'a model'},
                                 'serial': '003'})
             ]
    old_hexsha = inventory.repo.git.get_hexsha()
    onyo_new(inventory,
             directory=inventory.root / "empty",
             keys=specs)  # pyre-ignore[6]
    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha

    for s in specs:
        p = inventory.root / "empty" / f"{s['type']}_{s['make']}_{s['model.name']}.{s['serial']}"
        assert inventory.repo.is_asset_path(p)
        assert p in inventory.repo.git.files
        new_asset = inventory.get_item(p)
        assert new_asset.get("onyo.path.absolute") == p
        assert all(new_asset[k] == s[k] for k in s.keys())

    # faux serial and 'directory' key
    specs = [DotNotationWrapper({'type': 'A',
                                 'make': 'faux',
                                 'model': {'name': 'serial'},
                                 'directory': 'brandnew',
                                 'serial': 'faux'}),
             DotNotationWrapper({'type': 'Another',
                                 'make': 'faux',
                                 'model': {'name': 'serial'},
                                 'directory': 'completely/elsewhere',
                                 'serial': 'faux'})
             ]
    # 'directory' is in conflict with `directory` being given:
    pytest.raises(ValueError,
                  onyo_new,
                  inventory,
                  directory=inventory.root / "empty",
                  keys=specs)
    # w/o `directory` everything is fine:
    onyo_new(inventory,
             keys=specs)  # pyre-ignore[6]
    # another commit added
    assert inventory.repo.git.get_hexsha('HEAD~2') == old_hexsha

    for s in specs:
        files = [p
                 for p in (inventory.root / f"{s['directory']}").iterdir()
                 if p.name != OnyoRepo.ANCHOR_FILE_NAME
                 ]
        assert len(files) == 1
        # expected filename (except serial):
        assert files[0].name.startswith(f"{s['type']}_{s['make']}_{s['model.name']}.")
        assert inventory.repo.is_asset_path(files[0])
        assert files[0] in inventory.repo.git.files
        new_asset = inventory.get_item(files[0])
        assert new_asset.get("onyo.path.absolute") == files[0]
        assert new_asset.get("onyo.path.parent") == files[0].parent.relative_to(inventory.root)
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
    specs = [DotNotationWrapper({'type': 'flavor',
                                 'make': 'manufacturer',
                                 'model': {'name': 'exquisite'},
                                 'template': 'laptop.example',
                                 'serial': '1234'})]
    onyo_new(inventory,
             keys=specs)  # pyre-ignore[6]
    # another commit added
    assert inventory.repo.git.get_hexsha('HEAD~3') == old_hexsha
    expected_path = inventory.root / f"{specs[0]['type']}_{specs[0]['make']}_{specs[0]['model.name']}.{specs[0]['serial']}"
    assert inventory.repo.is_asset_path(expected_path)
    assert expected_path in inventory.repo.git.files
    asset_content = inventory.get_item(expected_path)
    # check for template keys:
    # (Note: key must be there - no `KeyError`; but content is `None`)
    for k in ['RAM', 'Size', 'USB']:
        assert asset_content[k] is None
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_creates_directories(inventory: Inventory) -> None:
    r"""`onyo_new()` must create new directories and subdirectories when called
    on a `directory` that does not yet exist, and add assets correctly to it.
    """
    specs = [{'type': 'a type',
              'make': 'I made it',
              'model': {'name': 'a model'},
              'serial': '002'},
             {'type': 'a type',
              'make': 'I made it',
              'model': {'name': 'a model'},
              'serial': '003'}]
    new_directory = inventory.root / "does" / "not" / "yet" / "exist"
    old_hexsha = inventory.repo.git.get_hexsha()

    onyo_new(inventory,
             directory=new_directory,
             keys=specs)  # pyre-ignore[6]

    # exactly one commit added
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha

    # the new directories exist
    assert new_directory.is_dir()
    assert (new_directory / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files
    assert (inventory.root / "does" / OnyoRepo.ANCHOR_FILE_NAME) in inventory.repo.git.files

    # new assets are added
    for s in specs:
        p = new_directory / inventory.generate_asset_name(Item(s, repo=inventory.repo))
        assert inventory.repo.is_asset_path(p)
        assert p in inventory.repo.git.files
        new_asset = inventory.get_item(p)
        assert new_asset.get("onyo.path.absolute") == p
        assert all(new_asset[k] == s[k] for k in s.keys())
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_edit(inventory: Inventory, monkeypatch) -> None:
    directory = inventory.root / "edited"
    monkeypatch.setenv('EDITOR', "printf 'key: value  #w/ comment' >>")

    specs = [{'template': 'empty',
              'model': {'name': 'MODEL'},
              'make': 'MAKER',
              'type': 'TYPE',
              'serial': 'totally_random'}]
    onyo_new(inventory,
             keys=specs,  # pyre-ignore[6]
             directory=directory,
             edit=True)
    expected_path = directory / "TYPE_MAKER_MODEL.totally_random"
    assert inventory.repo.is_asset_path(expected_path)
    assert expected_path in inventory.repo.git.files
    asset_content = inventory.get_item(expected_path)
    assert asset_content['key'] == 'value'
    assert 'key: value  #w/ comment' in expected_path.read_text()
    assert 'None' not in list(inventory.get_history(expected_path, n=1))[0]['message']
    # file already exists:
    edit_str = "model:\n  name: MODEL\nmake: MAKER\ntype: TYPE\n"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty',
              'serial': 'totally_random'}]

    pytest.raises(ValueError, onyo_new, inventory, keys=specs, directory=directory, edit=True)

    # asset already exists (but elsewhere - see fixture):
    edit_str = "model:\n  name: MODEL\nmake: MAKER\ntype: TYPE\nserial: SERIAL\n"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty'}]
    pytest.raises(ValueError, onyo_new, inventory, keys=specs, directory=directory, edit=True)
    assert inventory.repo.git.is_clean_worktree()

    # missing required fields:
    specs = [{'template': 'empty'}]
    monkeypatch.setenv('EDITOR', "printf 'key: value' >>")
    pytest.raises(ValueError, onyo_new, inventory, keys=specs, directory=directory, edit=True)

    # content should be exactly as expected
    # (empty files used to serialize to '{}')
    edit_str = "model:\n  name: MODEL\nmake: MAKER\ntype: TYPE\nserial: 8675309\n"
    monkeypatch.setenv('EDITOR', f"printf '{edit_str}' >>")
    specs = [{'template': 'empty'}]
    onyo_new(inventory,
             keys=specs,  # pyre-ignore[6]
             directory=directory,
             edit=True)
    expected_content = '---\n' + edit_str
    expected_path = directory / "TYPE_MAKER_MODEL.8675309"
    assert expected_content == expected_path.read_text()
    assert 'None' not in list(inventory.get_history(expected_path, n=1))[0]['message']


@pytest.mark.ui({'yes': True})
def test_onyo_new_clones(inventory: Inventory) -> None:
    existing_asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    existing_asset = inventory.get_item(existing_asset_path)
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
    new_asset = inventory.get_item(new_asset_path1)
    # equals existing asset except for path-pseudo-keys and serial:
    # Actually: history differs as well. onyo.is. doesn't, though
    for k, v in existing_asset.items():
        if k != "serial" and not k.startswith('onyo.path.') and not k.startswith('onyo.was.'):
            assert v == new_asset[k], f"{k}: {v} != {new_asset[k]}"
    assert all(v == new_asset[k] for k, v in existing_asset.items()
               if k != "serial" and not k.startswith('onyo.path') and not k.startswith('onyo.was.'))
    assert new_asset['serial'] == 'ANOTHER'

    # second new asset
    new_asset_path2 = asset_dir / f"{existing_asset_path.name.split('.')[0]}.whatever"
    assert inventory.repo.is_asset_path(new_asset_path2)
    new_asset = inventory.get_item(new_asset_path2)
    # equals existing asset except for path-pseudo-keys and serial:
    assert all(v == new_asset[k] for k, v in existing_asset.items()
               if k != "serial" and not k.startswith('onyo.path') and not k.startswith('onyo.was.'))
    assert new_asset['serial'] == 'whatever'
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_new_asset_dir(inventory: Inventory) -> None:
    new_asset_dir = inventory.root / "a_b_c.1"
    old_hexsha = inventory.repo.git.get_hexsha()
    onyo_new(inventory,
             keys=[{"type": "a",
                    "make": "b",
                    "model": {"name": "c"},
                    "serial": "1",
                    "onyo.is.directory": True}])
    assert inventory.repo.is_asset_dir(new_asset_dir)
    assert inventory.repo.git.is_clean_worktree()
    assert inventory.repo.git.get_hexsha('HEAD~1') == old_hexsha


@pytest.mark.ui({'yes': True})
@pytest.mark.parametrize('message', ["", None, "message with spe\"cial\\char\'acteஞrs"])
@pytest.mark.parametrize('auto_message', [True, False])
def test_onyo_new_commit_msg(inventory: Inventory,
                             message,
                             auto_message) -> None:
    onyo_new(inventory,
             keys=[{"type": "a",
                    "make": "b",
                    "model": {"name": "c"},
                    "serial": "faux"}],
             message=message,
             auto_message=auto_message)

    check_commit_msg(inventory, message, auto_message, "new [")
