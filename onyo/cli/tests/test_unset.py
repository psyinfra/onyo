import subprocess
from pathlib import Path
from typing import Any, Generator

import pytest

from onyo.lib.onyo import OnyoRepo


def convert_contents(
        raw_assets: list[tuple[str, dict[str, Any]]]) -> Generator:
    """Convert content dictionary to a plain-text string."""
    for file, raw_contents in raw_assets:
        contents = ''
        for k, v in raw_contents.items():
            if isinstance(v, str):
                v = f"'{v}'"
            elif isinstance(v, bool):
                v = str(v).lower()
            contents += f'{k}: {v}\n'
        yield [file, contents]


asset_contents = [
    ('laptop_apple_macbookpro.1', {'num': 8,
                                   'str': 'foo',
                                   'bool': True,
                                   'type': 'laptop',
                                   'make': 'apple',
                                   'model': 'macbookpro',
                                   'serial': '1'}),
    ('one/laptop_dell_precision.2', {'num': '16',
                                     'str': 'bar',
                                     'bool': False,
                                     'type': 'laptop',
                                     'make': 'dell',
                                     'model': 'precision',
                                     'serial': '2'}),
    ('one/two/headphones_apple_pro.3', {'num': '8',
                                        'str': 'bar',
                                        'bool': 'True',
                                        'type': 'headphones',
                                        'make': 'apple',
                                        'model': 'pro',
                                        'serial': '3'}),
    ('abc/def/monitor_dell_pro.4', {'str': 'foo=bar',
                                    'type': 'monitor',
                                    'make': 'dell',
                                    'model': 'pro',
                                    'serial': '4'}),
    ('laptop_dell_precision.2', {'num': '16',
                                 'str': 'bar',
                                 'bool': False,
                                 'type': 'laptop',
                                 'make': 'dell',
                                 'model': 'precision',
                                 'serial': '2'}),
    ('headphones_apple_pro.3', {'num': '8',
                                'str': 'bar',
                                'bool': 'True',
                                'type': 'headphones',
                                'make': 'apple',
                                'model': 'pro',
                                'serial': '3'}),
    ('monitor_dell_pro.4', {'str': 'foo=bar',
                            'type': 'monitor',
                            'make': 'dell',
                            'model': 'pro',
                            'serial': '4'}),
    ('headphones_dell_pro.4', {'num': '10GB',
                               'str': 'bar',
                               'type': 'headphones',
                               'make': 'dell',
                               'model': 'pro',
                               'serial': '4'}),
    ('one/two/three/headphones_apple_pro.4', {'num': '10GB',
                                              'type': 'headphones',
                                              'make': 'apple',
                                              'model': 'pro',
                                              'serial': '4'}),
    ('one/two/three/four/headphones_apple_pro.5', {'num': '10GB',
                                                   'type': 'headphones',
                                                   'make': 'apple',
                                                   'model': 'pro',
                                                   'serial': '5'}),
    ('another/dir/headphones_apple_pro.5', {'type': 'headphones',
                                            'make': 'apple',
                                            'model': 'pro',
                                            'serial': '5'}),
    ('a13bc_foo_bar.1', {'num': 'num-3',
                         'type': 'a13bc',
                         'make': 'foo',
                         'model': 'bar',
                         'serial': '1'}),
    ('a2cd_foo_bar.2', {'num': 'num-16',
                        'type': 'a2cd',
                        'make': 'foo',
                        'model': 'bar',
                        'serial': '2'}),
    ('a36ab_foo_bar.3', {'num': 'num-20',
                         'type': 'a36ab',
                         'make': 'foo',
                         'model': 'bar',
                         'serial': '3'}),
]


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('asset', [t[0] for t in asset_contents if "num" in t[1]])
@pytest.mark.parametrize('key', ['num'])
def test_unset(repo: OnyoRepo,
               asset: str,
               key: str) -> None:
    """Test that `onyo unset KEY <asset>` removes keys from of assets."""
    ret = subprocess.run(['onyo', '--yes', 'unset', '--keys', key, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert asset in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    assert key not in Path(asset).read_text()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('asset', [t[0] for t in asset_contents if "num" in t[1]])
@pytest.mark.parametrize('key', ['num'])
def test_unset_interactive(repo: OnyoRepo,
                           asset: str,
                           key: str) -> None:
    """Test that `onyo unset KEY <asset>` removes keys from of assets."""
    ret = subprocess.run(['onyo', 'unset', '--keys', key, '--asset', asset], input='y',
                         capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert asset in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    assert key not in Path(asset).read_text()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" not in t[1]]))
@pytest.mark.parametrize('asset', [t[0] for t in asset_contents if "num" not in t[1]])
def test_unset_key_does_not_exist(repo: OnyoRepo,
                                  asset: str) -> None:
    """Test that `onyo unset --keys KEY --asset ASSET` does not error when one of the KEYs does not
    exist."""
    no_key = "non_existing"

    # test un-setting a non-existing key from an empty file
    ret = subprocess.run(['onyo', '--yes', 'unset', '--keys', no_key, '--asset', asset],
                         capture_output=True, text=True)

    # verify reaction of onyo
    assert "No assets" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('key', ['num'])
def test_unset_multiple_assets(repo: OnyoRepo,
                               key: str) -> None:
    """Test that `onyo unset --keys KEY --asset ASSET [ASSET2 ...]` removes keys from of assets."""
    assets = repo.get_asset_paths()

    # test unsetting keys for multiple assets:
    ret = subprocess.run(['onyo', '--yes', 'unset', '--keys', key, '--asset', *assets],
                         capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    for asset in [a.relative_to(repo.git.root) for a in assets]:
        assert str(asset) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    for asset in assets:
        assert key not in asset.read_text()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('no_assets', [
    ["single_non_existing.asset"],
    ["simple/single_non_existing.asset"],
    [asset_contents[0][0], "single_non_existing.asset"]])
@pytest.mark.parametrize('key', ['num'])
def test_unset_error_non_existing_assets(repo: OnyoRepo,
                                         no_assets: list[str],
                                         key: str) -> None:
    """Test that `onyo unset --keys KEY --asset ASSET` errors correctly for non-existing assets."""
    ret = subprocess.run(['onyo', 'unset', '--keys', key, '--asset', *no_assets],
                         capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert no_assets[-1] in ret.stderr
    assert ret.returncode == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('key', ['num'])
def test_unset_without_path(repo: OnyoRepo,
                            key: str) -> None:
    """Test that `onyo unset --keys KEY` without a given path selects all assets recursively."""
    ret = subprocess.run(['onyo', '--yes', 'unset', '--keys', key],
                         capture_output=True, text=True)

    # verify the output
    assert ret.returncode != 0
    assert repo.git.is_clean_worktree()
    assert "Usage:" in ret.stderr


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('asset', [t[0] for t in asset_contents if "num" in t[1]])
@pytest.mark.parametrize('key', ['num'])
def test_unset_discard_changes_single_assets(repo: OnyoRepo,
                                             asset: str,
                                             key: str) -> None:
    """Test that `onyo unset` discards changes for assets successfully."""
    # do an `onyo unset`, but answer "n" to discard the changes done by unset
    ret = subprocess.run(['onyo', 'unset', '--keys', key, '--asset', asset], input='n',
                         capture_output=True, text=True)

    assert f"-{key}" in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the key was not removed
    assert f"{key}" in Path(asset).read_text()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents if "num" in t[1]]))
@pytest.mark.parametrize('asset', [t[0] for t in asset_contents if "num" in t[1]])
@pytest.mark.parametrize('key', ['num'])
def test_unset_message_flag(repo: OnyoRepo,
                            asset: str,
                            key: str) -> None:
    """Test that `onyo unset --message msg` overwrites the default commit message with one specified
    by the user containing different special characters."""
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    ret = subprocess.run(['onyo', '--yes', 'unset', '--message', msg, '--keys', key,
                          '--asset', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I'], capture_output=True, text=True)
    assert msg in ret.stdout
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*convert_contents(
    [t for t in asset_contents if 'laptop_apple_macbookpro.1' in t[0]]))
@pytest.mark.parametrize('name_field', [
    ["type"],
    ["make"],
    ["model"],
    ["serial"],
    ["num", "type"]])
def test_unset_error_unset_name_fields(repo: OnyoRepo,
                                       name_field: list[str]) -> None:
    """Test that `onyo unset KEY <asset>` throws the correct error without printing the usual
    information (e.g. diff output), when called with a KEY that is a name field (type, make, model
    or/and serial number), not a content field.
    """
    asset = 'laptop_apple_macbookpro.1'
    ret = subprocess.run(['onyo', '--yes', 'unset', '--keys', *name_field,
                          '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "Can't unset" in ret.stderr
    assert ret.returncode == 1

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()
