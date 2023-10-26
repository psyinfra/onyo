import subprocess
from pathlib import Path

from onyo.lib import OnyoRepo
import pytest
from typing import List

directories = ['.',
               'simple',
               's p a c e s',
               's p a/c e s',
               'r/e/c/u/r/s/i/v/e',
               'very/very/very/deep'
               ]
asset_specs = [{'type': 'laptop',
                'make': 'apple',
                'model': 'macbookpro'},
               {'type': 'lap top',
                'make': 'ap ple',
                'model': 'mac book pro'}
               ]

assets = []
for i, d in enumerate(directories):
    for spec in asset_specs:
        spec['serial'] = str(i)
        name = f"{spec['type']}_{spec['make']}_{spec['model']}.{spec['serial']}"
        content = "\n".join(f"{key}: {value}" for key, value in spec.items())
        assets.append([f"{d}/{name}", content])

asset_paths = [a[0] for a in assets]

values = [["mode=single"],
          ["mode=double"], ["key=space bar"]]

non_existing_assets: List[List[str]] = [
    ["single_non_existing.asset"],
    ["simple/single_non_existing.asset"],
    [asset_paths[0], "single_non_existing.asset"]]


name_fields = [["type=desktop"],
               ["make=lenovo"],
               ["model=thinkpad"],
               ["serial=1234"],
               ["type=surface"], ["make=microsoft"], ["model=go"], ["serial=666"],
               ["key=value"], ["type=server"], ["other=content"], ["serial=777"],
               ["serial=faux"], ["different=value"]]


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets.
    """
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set_interactive(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets.
    """
    ret = subprocess.run(['onyo', 'set', '--keys', *set_values, '--path', asset], input='y', capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_multiple_assets(repo: OnyoRepo, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can update the contents of multiple
    assets in a single call.
    """
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', *asset_paths], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all assets are in output and updated, and the repository clean
    for asset in asset_paths:
        assert str(Path(asset)) in ret.stdout
        for value in set_values:
            assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('no_assets', non_existing_assets)
def test_set_error_non_existing_assets(repo: OnyoRepo,
                                       no_assets: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` errors correctly for:
    - non-existing assets on root
    - non-existing assets in directories
    - one non-existing asset in a list of existing ones
    """
    ret = subprocess.run(['onyo', 'set', '--keys', 'key=value',
                          '--path', *no_assets], capture_output=True, text=True)

    # verify output and the state of the repository
    assert not ret.stdout
    assert "The following paths are neither an inventory directory nor an asset:" in ret.stderr
    assert ret.returncode == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_with_dot_recursive(repo: OnyoRepo, set_values: list[str]) -> None:
    """
    Test that when `onyo set KEY=VALUE .` is called from the repository root,
    onyo selects all assets in the complete repo recursively.
    """
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values,
                          '--path', "."], capture_output=True, text=True)

    # verify that output mentions every asset
    assert "The following assets will be changed:" in ret.stdout
    for asset in asset_paths:
        assert str(Path(asset)) in ret.stdout

    # output must contain "+key: value" one time for each asset in repository
    for value in set_values:
        assert ret.stdout.count(f"+{value.replace('=', ': ')}") == len(asset_paths)
    assert not ret.stderr
    assert ret.returncode == 0
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_without_path(repo: OnyoRepo, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE` without a given path selects all assets in
    the repository, beginning with cwd.
    """
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values], capture_output=True, text=True)

    # verify that output contains one line per asset
    assert "The following assets will be changed:" in ret.stdout
    for asset in asset_paths:
        assert str(Path(asset)) in ret.stdout

    # one time for every asset in the repository
    # "+key: value" should mentioned one time for each asset in root
    for value in set_values:
        assert ret.stdout.count(f"+{value.replace('=', ': ')}") == len(asset_paths)
    assert not ret.stderr
    assert ret.returncode == 0
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('directory', directories)
@pytest.mark.parametrize('set_values', values)
def test_set_recursive_directories(repo: OnyoRepo, directory: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <directory>` updates contents of assets
    correctly.
    """
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', directory], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(directory)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    repo_assets = repo.asset_paths
    for asset in [asset for asset in Path(directory).iterdir() if asset in repo_assets]:
        for value in set_values:
            assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set_discard_changes_single_assets(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set` discards changes for assets successfully.
    """
    ret = subprocess.run(['onyo', 'set', '--keys', *set_values, '--path', asset], input='n', capture_output=True, text=True)

    # verify output for just dot, should be all in onyo root, but not recursive
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that changes are in output, but not written into the asset
    for value in set_values:
        assert f"+{value.replace('=', ': ')}" in ret.stdout
        assert value.replace("=", ": ") not in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_set_discard_changes_recursive(repo: OnyoRepo) -> None:
    """
    Test that `onyo set` discards changes for all assets successfully.
    """
    set_values = "key=discard"
    ret = subprocess.run(['onyo', 'set', '--keys', set_values], input='n', capture_output=True, text=True)

    # verify output for just dot, should be all in onyo root, but not recursive
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert "No assets updated." in ret.stdout
    assert ret.stdout.count("+key: discard") == len(repo.asset_paths)
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that no changes where written
    repo_assets = repo.asset_paths
    for asset in repo_assets:
        assert "key: discard" not in Path.read_text(asset)
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set_yes_flag(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set --yes KEY=VALUE <asset>` updates assets without prompt.
    """
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # should not be asked with --yes flag
    assert "Update assets? (y/n) " not in ret.stdout

    # verify changes, and the repository clean
    for value in set_values:
        assert f"+{value.replace('=', ': ')}" in ret.stdout
        assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set_message_flag(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    ret = subprocess.run(['onyo', '--yes', 'set', '--message', msg,
                          '--keys', *set_values, '--path', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I'], capture_output=True, text=True)
    assert msg in ret.stdout
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(assets[2])
def test_set_quiet_without_yes_flag(repo: OnyoRepo) -> None:
    """
    Test that `onyo set --quiet KEY=VALUE <asset>` errors correctly without the
    --yes flag.
    """
    ret = subprocess.run(['onyo', '--quiet', 'set', '--keys', "mode=single", '--path', repo.asset_paths[0]],
                         capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The --quiet flag requires --yes." in ret.stderr
    assert ret.returncode == 1

    # verify that the repository is in a clean state
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', values)
def test_set_quiet_flag(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set --quiet --yes KEY=VALUE <asset>` works correctly without
    output and user-response.
    """
    ret = subprocess.run(['onyo', '--yes', '--quiet', 'set', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify that output is completely empty
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that asset contents are updated
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))

    # verify that the repository is in a clean state
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_dryrun_flag(repo: OnyoRepo, set_values: list[str]) -> None:
    """
    Test that `onyo set --dry-run KEY=VALUE <asset>` displays correct
    diff-output without actually changing any assets.
    """
    ret = subprocess.run(['onyo', 'set', '--dry-run', '--keys', *set_values,
                          '--path', *asset_paths], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # should not be asked if no real changes are made
    assert "Update assets? (y/n) " not in ret.stdout

    # verify that all assets and changes are in diff output, but no changes in
    # the asset files are made
    for asset in asset_paths:
        assert str(Path(asset)) in ret.stdout
        for value in set_values:
            assert f"+{value.replace('=', ': ')}" in ret.stdout
            assert value.replace("=", ": ") not in Path.read_text(Path(asset))

    # check that the repository is still clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('set_values', values)
@pytest.mark.parametrize('depth', ['0', '1', '3', '10'])
def test_set_depth_flag(
        repo: OnyoRepo, set_values: list[str], depth: str) -> None:
    """
    Test correct behavior for `onyo set --depth N KEY=VALUE <assets>` for
    different values for `--depth N`.

    The test searches through the output to find returned assets and ensures
    the number of returned assets matches the expected number, and the
    returned assets do not have more parents than the specified depth.
    """
    cmd = ['onyo', 'set', '--depth', depth, '--keys', *set_values]
    ret = subprocess.run(cmd, input='n', capture_output=True, text=True)

    assert not ret.stderr
    assert ret.returncode == 0

    expected_paths = repo.asset_paths if depth == '0' \
        else [p for p in repo.asset_paths if depth != '0' and len(p.relative_to(repo.git.root).parents) <= int(depth)]

    for p in repo.asset_paths:
        if p in expected_paths:
            assert str(p) in ret.stdout
        else:
            assert str(p) not in ret.stdout


@pytest.mark.parametrize('set_values', values)
@pytest.mark.parametrize('depth,expected', [
    ('-1', 'depth values must be positive, but is -1'),
])
def test_set_depth_flag_error(
        repo: OnyoRepo, set_values: list[str], depth: str, expected: str) -> None:
    """
    Test correct behavior for `onyo set --depth N KEY=VALUE <assets>` when an
    invalid depth value is given.
    """
    cmd = ['onyo', 'set', '--depth', depth, '--keys', *set_values]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert not ret.stdout
    assert expected in ret.stderr
    assert ret.returncode == 1


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
def test_add_new_key_to_existing_content(repo: OnyoRepo, asset: str) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can be called two times with
    different `KEY`, and adds it without overwriting existing values.
    """
    set_1 = "change=one"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_1, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_1.replace("=", ": ") in ret.stdout
    assert set_1.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call again and add a different KEY, without overwriting existing contents
    set_2 = "different=key"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_2, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
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
@pytest.mark.parametrize('asset', asset_paths)
def test_set_overwrite_key(repo: OnyoRepo, asset: str) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can be called two times with
    different VALUE for the same KEY, and overwrites existing values correctly.
    """
    set_value = "value=original"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_value, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_value.replace("=", ": ") in ret.stdout
    assert set_value.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call again with same key, but different value
    set_value_2 = "value=updated"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_value_2, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
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
@pytest.mark.parametrize('asset', asset_paths)
def test_setting_new_values_if_some_values_already_set(repo: OnyoRepo, asset: str) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets and adds
    the correct output if called multiple times, and that the output is correct.
    """
    set_values = "change=one"
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_values.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call with two values, one of which is already set and should not appear
    # again in the output.
    set_values = ["change=one", "different=key"]
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
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
def test_values_already_set(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets once, and
    if called again with same valid values the command does display the correct
    info message without error, and the repository stays in a clean state.
    """

    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call `onyo set` again with the same values
    ret = subprocess.run(['onyo', '--yes', 'set', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify second output
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', asset_paths)
@pytest.mark.parametrize('set_values', name_fields)
def test_set_update_name_fields(repo: OnyoRepo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can successfully change the names of
    assets, when KEY is type, make, model or/and serial number. Test also, that
    faux serials can be set and name fields are recognized and can be updated
    when they are `onyo set` together with a list of content fields.
    """
    # TODO: This test is supposed to test whether we can set fields that are part of the
    #       asset names. There are four such fields. This test function generates a whopping 168 test cases!
    ret = subprocess.run(['onyo', '--yes', 'set', '--rename', '--keys', *set_values,
                          '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_update_many_faux_serial_numbers(repo: OnyoRepo) -> None:
    """
    Test that `onyo set --rename serial=faux <asset>` can successfully update
    many assets with new faux serial numbers in one call.
    """

    pytest.skip("TODO: faux serials not yet considered outside new. Needs to move (modify_asset)")
    # remember old assets before renaming
    old_asset_names = repo.asset_paths
    ret = subprocess.run(['onyo', '--yes', 'set', '--rename', '--keys',
                          'serial=faux', '--path', *asset_paths], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert len(asset_paths) == ret.stdout.count('.faux')
    assert not ret.stderr
    assert ret.returncode == 0

    # this does not work when called in set.py or onyo.py, because this test
    # function still has its own repo object, which does not get updated when
    # calling `onyo set` with subprocess.run()
    repo.clear_caches()

    # verify that the name fields were not added to the contents and the names
    # are actually new
    for file in repo.asset_paths:
        contents = Path.read_text(Path(file))
        assert file not in old_asset_names
        assert "faux" not in contents

    # verify state of repo is clean
    assert repo.git.is_clean_worktree()
