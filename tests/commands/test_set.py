import subprocess
from pathlib import Path

from onyo.lib import Repo
import pytest
from typing import List

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro']

directories = ['.',
               'simple',
               's p a c e s',
               's p a/c e s',
               'r/e/c/u/r/s/i/v/e',
               'very/very/very/deep'
               ]

assets: List[str] = [f"{d}/{f}.{i}" for f in files
                     for i, d in enumerate(directories)]

values = [["mode=single"],
          ["mode=double"], ["key=space bar"]]


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_set(repo: Repo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_set_interactive(repo: Repo, asset: str, set_values: list[str]) -> None:
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
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_multiple_assets(repo: Repo, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can update the contents of multiple
    assets in a single call.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', *assets], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all assets are in output and updated, and the repository clean
    for asset in assets:
        assert str(Path(asset)) in ret.stdout
        for value in set_values:
            assert value.replace("=", ": ") in Path.read_text(Path(asset))
    repo.fsck()


non_existing_assets: List[List[str]] = [
    ["single_non_existing.asset"],
    ["simple/single_non_existing.asset"],
    [assets[0], "single_non_existing.asset"]]
@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('no_assets', non_existing_assets)
def test_set_error_non_existing_assets(repo: Repo,
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
    assert "The following paths do not exist:" in ret.stderr
    assert ret.returncode == 1
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_with_dot_recursive(repo: Repo, set_values: list[str]) -> None:
    """
    Test that when `onyo set KEY=VALUE .` is called from the repository root,
    onyo selects all assets in the complete repo recursively.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values,
                          '--path', "."], capture_output=True, text=True)

    # verify that output mentions every asset
    assert "The following assets will be changed:" in ret.stdout
    for asset in assets:
        assert str(Path(asset)) in ret.stdout

    # output must contain "+key: value" one time for each asset in repository
    for value in set_values:
        assert ret.stdout.count(f"+{value.replace('=', ': ')}") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_without_path(repo: Repo, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE` without a given path selects all assets in
    the repository, beginning with cwd.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values], capture_output=True, text=True)

    # verify that output contains one line per asset
    assert "The following assets will be changed:" in ret.stdout
    for asset in assets:
        assert str(Path(asset)) in ret.stdout

    # one time for every asset in the repository
    # "+key: value" should mentioned one time for each asset in root
    for value in set_values:
        assert ret.stdout.count(f"+{value.replace('=', ': ')}") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('directory', directories)
@pytest.mark.parametrize('set_values', values)
def test_set_recursive_directories(repo: Repo, directory: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <directory>` updates contents of assets
    correctly.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', directory], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(directory)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    repo_assets = repo.assets
    for asset in [asset for asset in Path(directory).iterdir() if asset in repo_assets]:
        for value in set_values:
            assert value.replace("=", ": ") in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_set_discard_changes_single_assets(repo: Repo, asset: str, set_values: list[str]) -> None:
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
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_set_discard_changes_recursive(repo: Repo) -> None:
    """
    Test that `onyo set` discards changes for all assets successfully.
    """
    set_values = "key=discard"
    ret = subprocess.run(['onyo', 'set', '--keys', set_values], input='n', capture_output=True, text=True)

    # verify output for just dot, should be all in onyo root, but not recursive
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert "No assets updated." in ret.stdout
    assert ret.stdout.count("+key: discard") == len(repo.assets)
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that no changes where written
    repo_assets = repo.assets
    for asset in repo_assets:
        assert "key: discard" not in Path.read_text(asset)
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_set_yes_flag(repo: Repo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set --yes KEY=VALUE <asset>` updates assets without prompt.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

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
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_set_message_flag(repo: Repo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    ret = subprocess.run(['onyo', 'set', '--yes', '--message', msg,
                          '--keys', *set_values, '--path', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I'], capture_output=True, text=True)
    assert msg in ret.stdout
    repo.fsck()


asset = 'simple/laptop_apple_macbookpro.0'
@pytest.mark.repo_files(asset)
def test_set_quiet_without_yes_flag(repo: Repo) -> None:
    """
    Test that `onyo set --quiet KEY=VALUE <asset>` errors correctly without the
    --yes flag.
    """
    ret = subprocess.run(['onyo', 'set', '--quiet', '--keys', "mode=single", '--path', asset], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The --quiet flag requires --yes." in ret.stderr
    assert ret.returncode == 1

    # verify that the repository is in a clean state
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_set_quiet_flag(repo: Repo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set --quiet --yes KEY=VALUE <asset>` works correctly without
    output and user-response.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--quiet', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify that output is completely empty
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that asset contents are updated
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))

    # verify that the repository is in a clean state
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('set_values', values)
def test_set_dryrun_flag(repo: Repo, set_values: list[str]) -> None:
    """
    Test that `onyo set --dry-run KEY=VALUE <asset>` displays correct
    diff-output without actually changing any assets.
    """
    ret = subprocess.run(['onyo', 'set', '--dry-run', '--keys', *set_values,
                          '--path', *assets], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # should not be asked if no real changes are made
    assert "Update assets? (y/n) " not in ret.stdout

    # verify that all assets and changes are in diff output, but no changes in
    # the asset files are made
    for asset in assets:
        assert str(Path(asset)) in ret.stdout
        for value in set_values:
            assert f"+{value.replace('=', ': ')}" in ret.stdout
            assert value.replace("=", ": ") not in Path.read_text(Path(asset))

    # check that the repository is still clean
    repo.fsck()


@pytest.mark.repo_files(
    "laptop_macbook_pro.0",
    "dir1/laptop_macbook_pro.1",
    "dir1/dir2/laptop_macbook_pro.2",
    "dir1/dir2/dir3/laptop_macbook_pro.3",
    "dir1/dir2/dir3/dir4/laptop_macbook_pro.4",
    "dir1/dir2/dir3/dir4/dir5/laptop_macbook_pro.5",
    "dir1/dir2/dir3/dir4/dir5/dir6/laptop_macbook_pro.6",)
@pytest.mark.parametrize('set_values', values)
@pytest.mark.parametrize('depth,expected', [
    ('0', 7), ('1', 1), ('3', 3), ('6', 6), ('10', 7)
])
def test_set_depth_flag(
        repo: Repo, set_values: list[str], depth: str, expected: int) -> None:
    """
    Test correct behavior for `onyo set --depth N KEY=VALUE <assets>` for
    different values for `--depth N`.

    The test searches through the output to find returned assets and ensures
    the number of returned assets matches the expected number, and the
    returned assets do not have more parents than the specified depth.
    """
    cmd = ['onyo', 'set', '--depth', depth, '--keys', *set_values]
    ret = subprocess.run(cmd, input='n', capture_output=True, text=True)
    output = [output for output in ret.stdout.split('\n')]
    asset_paths = [str(a) for a in repo.relative_to_root(repo.assets)]
    n_assets = 0

    assert not ret.stderr
    assert ret.returncode == 0

    for line in output:
        if line not in asset_paths:
            continue

        n_assets += 1

        if depth != '0':
            assert len(Path(line).parents) <= int(depth)

    assert n_assets == expected


@pytest.mark.repo_files(
    "laptop_macbook_pro.0",
    "dir1/laptop_macbook_pro.1",
    "dir1/dir2/laptop_macbook_pro.2",
    "dir1/dir2/dir3/laptop_macbook_pro.3",
    "dir1/dir2/dir3/dir4/laptop_macbook_pro.4",
    "dir1/dir2/dir3/dir4/dir5/laptop_macbook_pro.5",
    "dir1/dir2/dir3/dir4/dir5/dir6/laptop_macbook_pro.6",)
@pytest.mark.parametrize('set_values', values)
@pytest.mark.parametrize('depth,expected', [
    ('-1', 'depth values must be positive, but is -1'),
])
def test_set_depth_flag_error(
        repo: Repo, set_values: list[str], depth: str, expected: str) -> None:
    """
    Test correct behavior for `onyo set --depth N KEY=VALUE <assets>` when an
    invalid depth value is given.
    """
    cmd = ['onyo', 'set', '--depth', depth, '--keys', *set_values]
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert not ret.stdout
    assert expected in ret.stderr
    assert ret.returncode == 1


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_add_new_key_to_existing_content(repo: Repo, asset: str) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can be called two times with
    different `KEY`, and adds it without overwriting existing values.
    """
    set_1 = "change=one"
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', set_1, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_1.replace("=", ": ") in ret.stdout
    assert set_1.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call again and add a different KEY, without overwriting existing contents
    set_2 = "different=key"
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', set_2, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_2.replace("=", ": ") in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # this line is already changed, it should not be in the output, but the file
    assert set_1.replace("=", ": ") not in ret.stdout
    assert set_1.replace("=", ": ") in Path.read_text(Path(asset))
    # this change is new, it has to be in the output and the file
    assert set_2.replace("=", ": ") in ret.stdout
    assert set_2.replace("=", ": ") in Path.read_text(Path(asset))

    # verify state of repo is clean
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_set_overwrite_key(repo: Repo, asset: str) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can be called two times with
    different VALUE for the same KEY, and overwrites existing values correctly.
    """
    set_value = "value=original"
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', set_value, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_value.replace("=", ": ") in ret.stdout
    assert set_value.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call again with same key, but different value
    set_value_2 = "value=updated"
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', set_value_2, '--path', asset], capture_output=True, text=True)

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
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_setting_new_values_if_some_values_already_set(repo: Repo, asset: str) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets and adds
    the correct output if called multiple times, and that the output is correct.
    """
    set_values = "change=one"
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert set_values.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call with two values, one of which is already set and should not appear
    # again in the output.
    set_values = ["change=one", "different=key"]
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # this line is already changed, it should not be in the output, but the file
    assert "change=one".replace("=", ": ") not in ret.stdout
    assert "change=one".replace("=", ": ") in Path.read_text(Path(asset))

    # this change is new, it has to be in the output
    assert "different=key".replace("=", ": ") in ret.stdout
    assert "different=key".replace("=", ": ") in Path.read_text(Path(asset))

    # verify state of repo is clean
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', values)
def test_values_already_set(repo: Repo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` updates contents of assets once, and
    if called again with same valid values the command does display the correct
    info message without error, and the repository stays in a clean state.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    for value in set_values:
        assert value.replace("=", ": ") in Path.read_text(Path(asset))
    assert not ret.stderr
    assert ret.returncode == 0

    # call `onyo set` again with the same values
    ret = subprocess.run(['onyo', 'set', '--yes', '--keys', *set_values, '--path', asset], capture_output=True, text=True)

    # verify second output
    assert "The values are already set. No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify state of repo is clean
    repo.fsck()


name_fields = [["type=desktop"],
               ["make=lenovo"],
               ["model=thinkpad"],
               ["serial=1234"],
               ["type=surface"], ["make=microsoft"], ["model=go"], ["serial=666"],
               ["key=value"], ["type=server"], ["other=content"], ["serial=777"],
               ["serial=faux"], ["different=value"]]
@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('set_values', name_fields)
def test_set_update_name_fields(repo: Repo, asset: str, set_values: list[str]) -> None:
    """
    Test that `onyo set KEY=VALUE <asset>` can successfully change the names of
    assets, when KEY is type, make, model or/and serial number. Test also, that
    faux serials can be set and name fields are recognized and can be updated
    when they are `onyo set` together with a list of content fields.
    """
    ret = subprocess.run(['onyo', 'set', '--yes', '--rename', '--keys', *set_values,
                          '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the name fields were not added to the contents
    for file in repo.assets:
        contents = Path.read_text(Path(file))
        assert not any(field in contents for field in ['type', 'make', 'model', 'serial'])

    # verify state of repo is clean
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_update_many_faux_serial_numbers(repo: Repo) -> None:
    """
    Test that `onyo set --rename serial=faux <asset>` can successfully update
    many assets with new faux serial numbers in one call.
    """
    # remember old assets before renaming
    old_asset_names = repo.assets
    ret = subprocess.run(['onyo', 'set', '--yes', '--rename', '--keys',
                          'serial=faux', '--path', *assets], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert len(assets) == ret.stdout.count('faux')
    assert not ret.stderr
    assert ret.returncode == 0

    # this does not work when called in set.py or onyo.py, because this test
    # function still has its own repo object, which does not get updated when
    # calling `onyo set` with subprocess.run()
    repo.clear_caches()

    # verify that the name fields were not added to the contents and the names
    # are actually new
    for file in repo.assets:
        contents = Path.read_text(Path(file))
        assert file not in old_asset_names
        assert "serial" not in contents and "faux" not in contents

    # verify state of repo is clean
    repo.fsck()
