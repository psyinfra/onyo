from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from onyo.lib.onyo import OnyoRepo
from onyo.lib.utils import (
    dict_to_asset_yaml,
    DotNotationWrapper,
)

if TYPE_CHECKING:
    from typing import List

directories = ['.',
               'simple',
               's p a c e s',
               's p a/c e s',
               'r/e/c/u/r/s/i/v/e',
               'very/very/very/deep'
               ]
asset_specs = [DotNotationWrapper({'type': 'laptop',
                                   'make': 'apple',
                                   'model': {'name': 'macbookpro'}}),
               DotNotationWrapper({'type': 'lap top',
                                   'make': 'ap ple',
                                   'model': {'name': 'mac book pro'}})
               ]

assets = []
for i, d in enumerate(directories):
    for spec in asset_specs:
        spec['serial'] = "00_" + str(i)
        name = f"{spec['type']}_{spec['make']}_{spec['model.name']}.{spec['serial']}"
        content = dict_to_asset_yaml(spec)
        assets.append([f"{d}/{name}", content])

asset_paths = [a[0] for a in assets]

values = [["mode=single"],
          ["mode=double"],
          ["key=space bar"],
          ["nested.key=something"]]

non_existing_assets: List[List[str]] = [
    ["single_non_existing.asset"],
    ["simple/single_non_existing.asset"],
    [asset_paths[0], "single_non_existing.asset"]]


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set(repo: OnyoRepo,
             asset: str,
             set_values: list[str]) -> None:
    r"""``onyo set KEY=VALUE --asset <asset>`` updates the contents of assets."""

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    file_content = Path.read_text(Path(asset))
    for value in set_values:
        k, v = value.split('=')
        if '.' in k:
            assert f"{k.split('.')[0]}:" in file_content
            assert f"{k.split('.')[1]}: {v}" in file_content
        else:
            assert f"{k}: {v}" in file_content
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [asset_paths[0]])
@pytest.mark.parametrize('set_values', values)
def test_set_interactive(repo: OnyoRepo,
                         asset: str,
                         set_values: list[str]) -> None:
    r"""``onyo set KEY=VALUE --asset <asset>`` updates contents of assets."""

    ret = subprocess.run(['onyo', 'set', '--keys', *set_values, '--asset', asset],
                         input='y', capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    file_content = Path.read_text(Path(asset))
    for value in set_values:
        k, v = value.split('=')
        if '.' in k:
            assert f"{k.split('.')[0]}:" in file_content
            assert f"{k.split('.')[1]}: {v}" in file_content
        else:
            assert f"{k}: {v}" in file_content
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_multiple_assets(repo: OnyoRepo,
                             set_values: list[str]) -> None:
    r"""Update the contents of multiple assets in a single call."""

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values,
                          '--asset', *asset_paths],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all assets are in output and updated, and the repository clean
    for asset in asset_paths:
        assert str(Path(asset)) in ret.stdout
        file_content = Path.read_text(Path(asset))
        for value in set_values:
            k, v = value.split('=')
            if '.' in k:
                assert f"{k.split('.')[0]}:" in file_content
                assert f"{k.split('.')[1]}: {v}" in file_content
            else:
                assert f"{k}: {v}" in file_content
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('no_assets', non_existing_assets)
def test_set_error_non_existing_assets(repo: OnyoRepo,
                                       no_assets: list[str]) -> None:
    r"""Error when passed a non-existing asset."""

    ret = subprocess.run(['onyo', 'set', '--keys', 'key=value',
                          '--asset', *no_assets], capture_output=True, text=True)

    # verify output and the state of the repository
    assert not ret.stdout
    assert "The following paths aren't assets:" in ret.stderr
    assert ret.returncode == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_without_path(repo: OnyoRepo,
                          set_values: list[str]) -> None:
    r"""Error when not passed a path."""

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values],
                         capture_output=True, text=True)

    assert ret.returncode != 0
    assert "usage:" in ret.stderr  # argparse should already complain
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [asset_paths[0]])
@pytest.mark.parametrize('set_values', values)
def test_set_discard_changes_single_assets(repo: OnyoRepo,
                                           asset: str,
                                           set_values: list[str]) -> None:
    r"""Don't modify when the user responds "n"."""

    ret = subprocess.run(['onyo', 'set', '--keys', *set_values, '--asset', asset],
                         input='n',
                         capture_output=True, text=True)

    # verify output for just dot, should be all in onyo root, but not recursive
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that changes are in output, but not written into the asset
    file_content = Path.read_text(Path(asset))
    for value in set_values:
        k, v = value.split('=')
        if '.' in k:
            assert f"+{k.split('.')[0]}:" in ret.stdout
            assert f"{k.split('.')[0]}:" not in file_content
            assert f"+  {k.split('.')[1]}: {v}" in ret.stdout
            assert f"{k.split('.')[1]}: {v}" not in file_content
        else:
            assert f"+{k}: {v}" in ret.stdout
            assert f"{k}: {v}" not in file_content
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [asset_paths[0]])
def test_add_new_key_to_existing_content(repo: OnyoRepo,
                                         asset: str) -> None:
    r"""Call ``set` two times with different keys, and don't alter unrelated values."""

    set_1 = "change=one"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_1, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_1.replace("=", ": ") in ret.stdout
    assert set_1.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call again and add a different KEY, without overwriting existing contents
    set_2 = "different=key"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_2, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_2.replace("=", ": ") in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # This line is unchanged, it should still be the file.
    # Whether and how it shows up in the output depends on how a diff is shown.
    assert set_1.replace("=", ": ") in Path.read_text(Path(asset))
    # this change is new, it has to be part of the diff in the output and the file
    assert set_2.replace("=", ": ") in ret.stdout
    assert set_2.replace("=", ": ") in Path.read_text(Path(asset))

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [asset_paths[0]])
def test_set_overwrite_key(repo: OnyoRepo,
                           asset: str) -> None:
    r"""Set the same key twice in different runs."""

    set_value = "value=original"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_value, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_value.replace("=", ": ") in ret.stdout
    assert set_value.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call again with same key, but different value
    set_value_2 = "value=updated"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_value_2, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{set_value}".replace("=", ": ") in ret.stdout
    assert f"+{set_value_2}".replace("=", ": ") in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # check that the second value is set in asset
    assert set_value_2.replace("=", ": ") in Path.read_text(Path(asset))

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [asset_paths[0]])
def test_setting_new_values_if_some_values_already_set(repo: OnyoRepo,
                                                       asset: str) -> None:
    r"""The correct output is generated when called multiple times."""

    set_values = "change=one"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_values, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_values.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call with two values, one of which is already set and should not appear
    # again in the output.
    set_values = ["change=one", "different=key"]
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # This line is unchanged, it should still be the file.
    # Whether and how it shows up in the output depends on how a diff is shown.
    assert "change=one".replace("=", ": ") in Path.read_text(Path(asset))

    # this change is new, it has to be in the output
    assert "different=key".replace("=", ": ") in ret.stdout
    assert "different=key".replace("=", ": ") in Path.read_text(Path(asset))

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(assets[0])
@pytest.mark.parametrize('asset', [asset_paths[0]])
@pytest.mark.parametrize('set_values', values)
def test_values_already_set(repo: OnyoRepo,
                            asset: str,
                            set_values: list[str]) -> None:
    r"""The same call twice results in 1) changes and 2) no changes."""

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values,
                          '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert "Modified assets:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    file_content = Path.read_text(Path(asset))
    for value in set_values:
        k, v = value.split('=')
        if '.' in k:
            assert f"{k.split('.')[0]}:" in file_content
            assert f"{k.split('.')[1]}: {v}" in file_content
        else:
            assert f"{k}: {v}" in file_content

    assert not ret.stderr
    assert ret.returncode == 0

    # call `onyo set` again with the same values
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--asset', asset],
                         capture_output=True, text=True)

    # verify second output
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_update_many_faux_serial_numbers(repo: OnyoRepo) -> None:
    r"""Generate faux serials for many assets in one call."""

    pytest.skip("TODO: faux serials not yet considered outside new. Needs to move (modify_asset)")
    # remember old assets before renaming
    old_asset_names = repo.asset_paths
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys',
                          'serial=faux', '--asset', *asset_paths], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert len(asset_paths) == ret.stdout.count('.faux')
    assert not ret.stderr
    assert ret.returncode == 0

    # this does not work when called in set.py or onyo.py, because this test
    # function still has its own repo object, which does not get updated when
    # calling `onyo set` with subprocess.run()
    repo.clear_cache()

    # verify that the name fields were not added to the contents and the names
    # are actually new
    for file in repo.asset_paths:
        contents = Path.read_text(Path(file))
        assert file not in old_asset_names
        assert "faux" not in contents

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(assets[0])
@pytest.mark.parametrize('asset', [asset_paths[0]])
@pytest.mark.parametrize('set_values', values)
def test_duplicate_keys(repo: OnyoRepo,
                        asset: str,
                        set_values: list[str]) -> None:
    r"""Error if the same key is passed multiple times."""

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys',
                          *set_values, 'dup.key=1', 'dup.key=2', '--asset', asset],
                         capture_output=True, text=True)

    # verify output
    assert ret.returncode == 2
    assert "Keys must not be given multiple times." in ret.stderr
    assert not ret.stdout

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(assets[0])
@pytest.mark.parametrize('asset', [asset_paths[0]])
def test_set_empty_dictlist(repo: OnyoRepo, asset: str) -> None:
    r"""Test special symbols {}, <dict>, [], <list> to set empty dicts/lists."""

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys',
                          'new.dict={}', 'new.list=[]', '--asset', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert "new:" in ret.stdout
    assert "dict: {}" in ret.stdout
    assert "list: []" in ret.stdout
    ret = subprocess.run(['onyo', 'get', '-H', '--keys', 'path', '--match', 'new.dict={}', 'new.list=[]'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert Path(asset).name in ret.stdout

    # now use `<dict>` and `<list>` instead and swap keys in order to overwrite:
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys',
                          'new.dict=<list>', 'new.list=<dict>', '--asset', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert "new:" in ret.stdout
    assert "dict: []" in ret.stdout
    assert "list: {}" in ret.stdout

    # we swapped the keys, so old matching criterion should NOT work:
    ret = subprocess.run(['onyo', 'get', '-H', '--keys', 'path', '--match', 'new.dict={}', 'new.list=[]'],
                         capture_output=True, text=True)
    assert ret.returncode == 1

    # correct query
    ret = subprocess.run(['onyo', 'get', '-H', '--keys', 'path', '--match', 'new.dict=[]', 'new.list={}'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert Path(asset).name in ret.stdout
