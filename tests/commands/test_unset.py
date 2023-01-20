import subprocess
from pathlib import Path

from onyo.lib import Repo
import pytest

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro']

directories = ['.',
               'simple',
               's p a c e s',
               's p a/c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'very/very/very/deep']

assets = [f"{d}/{f}.{i}" for f in files for i, d in enumerate(directories)]


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_unset(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset KEY <asset>` removes keys from of assets.
    """
    set_values = "key=value"
    key = "key"

    # TODO: find out if there is a faster way than `onyo set` for writing
    # without leaving an unclean git tree
    ret = subprocess.run(['onyo', 'set', set_values, asset], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "key: value" in Path.read_text(Path(asset))

    ret = subprocess.run(['onyo', 'unset', key, asset], input='y', capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    assert "key: value" not in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_unset_subset_of_keys(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset KEY <asset>` removes just the keys specified from
    assets with many other keys.
    """
    set_values = ["first=value", "key=value", "second=key"]
    key = "key"
    ret = subprocess.run(['onyo', 'set'] + set_values + [asset], input='y', capture_output=True, text=True)
    assert ret.returncode == 0

    # test un-setting just a subset of the existing keys
    ret = subprocess.run(['onyo', 'unset', key, asset], input='y', capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify the right key is removed and the others still exist, and that the
    # repository is still in a clean state
    contents = Path.read_text(Path(asset))
    assert "key: value" not in contents
    assert "first: value" in contents
    assert "second: key" in contents
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_error_unset_non_existing_key(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset KEY <asset>` prints the correct info without stopping
    the command, when one of the KEYs does not exist.
    Calls `onyo unset KEY <asset>` on an completely empty asset, and then
    `onyo unset KEY1,KEY2 <asset>` on an asset containing KEY2, but not KEY1.
    """
    set_values = "existing=key"
    no_key = "non_existing"

    # test un-setting a non-existing key from an empty file
    ret = subprocess.run(['onyo', 'unset', no_key, asset], capture_output=True, text=True)
    assert "No assets containing the specified key(s) could be found. No assets updated." in ret.stdout
    assert f"Field {no_key} does not exist in " in ret.stderr
    assert ret.returncode == 0

    # set key so the asset is not empty
    ret = subprocess.run(['onyo', 'set', set_values, asset], input='y', capture_output=True, text=True)
    assert ret.returncode == 0

    # test un-setting a non-existing key from an asset with other keys
    ret = subprocess.run(['onyo', 'unset', "non_existing,existing", asset], input='y', capture_output=True, text=True)
    assert "-existing: key" in ret.stdout
    assert f"Field {no_key} does not exist in " in ret.stderr
    assert ret.returncode == 0

    # verify the other key got removed anyways, and the repository is clean
    assert "existing: key" not in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_unset_multiple_assets(repo: Repo) -> None:
    """
    Test that `onyo unset KEY <asset>` removes keys from of assets.
    """
    set_values = "key=value"
    key = "key"

    ret = subprocess.run(['onyo', 'set', set_values] + list(assets), input='y', capture_output=True, text=True)
    assert ret.returncode == 0

    # test unsetting multiple keys:
    ret = subprocess.run(['onyo', 'unset', key] + list(assets), input='y', capture_output=True, text=True)
    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    for asset in repo.assets:
        assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    for asset in repo.assets:
        assert key not in Path.read_text(Path(asset))
    repo.fsck()


non_existing_assets = [["single_non_existing.asset"],
                       ["simple/single_non_existing.asset"],
                       [assets[0], "single_non_existing.asset"]]
@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('no_assets', non_existing_assets)
def test_unset_error_non_existing_assets(repo: Repo, no_assets: list[str]) -> None:
    """
    Test that `onyo unset KEY <asset>` errors correctly for non-existing assets
    on root, in directories, or if an invalid asset name is in a list of
    valid ones.
    """
    ret = subprocess.run(['onyo', 'unset', 'key'] + no_assets, capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths do not exist:" in ret.stderr
    assert ret.returncode == 1
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_unset_with_dot(repo: Repo) -> None:
    """
    Test that when `onyo unset KEY=VALUE .` is called from the
    repository root, onyo uses all assets in the completely repo recursively.
    """
    key_values = "key=recursive"
    key = "key"

    # set values:
    ret = subprocess.run(['onyo', 'set', key_values, "."], input='y', capture_output=True, text=True)
    assert ret.stdout.count("+key: recursive") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()

    # unset `key` again
    ret = subprocess.run(['onyo', 'unset', key, "."], input='y', capture_output=True, text=True)

    # verify that output contains one line per asset
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    # one time for every asset in the repository
    assert ret.stdout.count("-key: recursive") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_unset_without_path(repo: Repo) -> None:
    """
    Test that `onyo unset KEY` without a given path argument selects all assets
    recursively.

    This uses first `onyo set` (and verifies success) to set all values, and
    then a similar `onyo unset` call to remove the keys.
    """
    set_values = "key=cwd_recursive"
    key = "key"

    # first set values for all the assets, to make sure that really just the
    # ones in root get removed, even if others with the same key exist
    ret = subprocess.run(['onyo', 'set', set_values, "."], input='y', capture_output=True, text=True)

    # verify success
    assert ret.stdout.count("+key: cwd_recursive") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()

    # unset `key` again
    ret = subprocess.run(['onyo', 'unset', key], input='y', capture_output=True, text=True)

    # verify the output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert ret.stdout.count("-key: cwd_recursive") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('directory', directories)
def test_unset_recursive_directories(repo: Repo, directory: str) -> None:
    """
    Test that `onyo unset KEY <directory>` updates contents of
    assets in <directory>.

    This uses first `onyo set` (and verifies success) to set all values, and
    then a similar `onyo unset` call to remove the keys.
    """
    set_values = "key=recursive_directories"
    key = "key"
    ret = subprocess.run(['onyo', 'set', set_values, "."], input='y', capture_output=True, text=True)

    # verify output
    assert str(Path(directory)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # unset values
    ret = subprocess.run(['onyo', 'unset', key, directory], input='y', capture_output=True, text=True)

    # verify changes, and the repository clean
    # TODO: update this after solving #259
    repo_assets = repo.assets
    for asset in [asset for asset in Path(directory).iterdir() if asset in repo_assets]:
        for value in set_values.split(","):
            assert key not in Path.read_text(Path(asset))
            assert "-key: recursive_directories" in ret.stdout
    repo.fsck()

@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_unset_discard_changes_single_assets(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset` discards changes for assets successfully.
    """
    set_values = "key=discard_value"
    key = "key"
    ret = subprocess.run(['onyo', 'set', set_values, asset], input='y', capture_output=True, text=True)

    assert str(Path(asset)) in ret.stdout
    assert "+key: discard_value" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # do an `onyo unset`, but answer "n" to discard the changes done by unset
    ret = subprocess.run(['onyo', 'unset', key, asset], input='n', capture_output=True, text=True)
    assert "-key: discard_value" in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the key was not removed
    assert "key: discard_value" in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_unset_discard_changes_recursive(repo: Repo) -> None:
    """
    Test that `onyo unset` discards changes for all assets successfully.
    """
    set_values = "key=discard"
    key = "key"
    ret = subprocess.run(['onyo', 'set', set_values], input='y', capture_output=True, text=True)

    # verify output for just dot, should be all in onyo root, but not recursive
    assert ret.stdout.count("+key: discard") == len(repo.assets)
    assert not ret.stderr
    assert ret.returncode == 0

    # call `unset`, but discard changes
    ret = subprocess.run(['onyo', 'unset', key], input='n', capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert "No assets updated." in ret.stdout
    assert ret.stdout.count("-key: discard") == len(repo.assets)
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the removal was not written but discarded
    repo_assets = repo.assets
    for asset in repo_assets:
        assert "key: discard" in Path.read_text(asset)
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_unset_yes_flag(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --yes KEY <asset>` updates assets without prompt.
    """
    set_values = "key=yes"
    key = "key"
    ret = subprocess.run(['onyo', 'set', '--yes', set_values, asset], capture_output=True, text=True)

    # remove the key again
    ret = subprocess.run(['onyo', 'unset', '--yes', key, asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{set_values.replace('=',': ')}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # should not be asked with --yes flag
    assert "Update assets? (y/n) " not in ret.stdout

    # verify that the removal did happen, and the repository is still clean
    assert "key" not in Path.read_text(Path(asset))
    repo.fsck()


asset = 'simple/laptop_apple_macbookpro.0'
@pytest.mark.repo_files(asset)
def test_unset_quiet_without_yes_flag(repo: Repo) -> None:
    """
    Test that `onyo unset --quiet KEY <asset>` errors correctly without
    the --yes flag.
    """
    ret = subprocess.run(['onyo', 'unset', '--quiet', "dummy_key", asset], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The --quiet flag requires --yes." in ret.stderr
    assert ret.returncode == 1

    # verify that the repository is in a clean state
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_unset_quiet_flag(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --quiet --yes KEY <asset>` works correctly without
    output and user-response.
    """
    set_values = "key=quiet"
    ret = subprocess.run(['onyo', 'set', '--yes', '--quiet', set_values, asset], capture_output=True, text=True)
    assert not ret.stderr
    assert ret.returncode == 0

    ret = subprocess.run(['onyo', 'unset', '--yes', '--quiet', "key", asset], capture_output=True, text=True)
    # verify that output is completely empty
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that asset contents are updated
    assert "key" not in Path.read_text(Path(asset))

    # verify that the repository is in a clean state
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_unset_dryrun_flag(repo: Repo) -> None:
    """
    Test that `onyo unset --dry-run KEY <asset>` displays correct diff-output
    without actually changing any assets.
    """
    set_values = "key=dry-run"
    key = "key"
    # set values normally
    ret = subprocess.run(['onyo', 'set', set_values] + list(assets), input='y', capture_output=True, text=True)
    assert not ret.stderr
    assert ret.returncode == 0

    # do a dry-run with unset, to check if the diff is correct without actually
    # changing an asset
    ret = subprocess.run(['onyo', 'unset', '--dry-run', key] + list(assets), capture_output=True, text=True)

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
        assert "-key: dry-run" in ret.stdout
        assert "key: dry-run" in Path.read_text(Path(asset))

    # check that the repository is still clean
    repo.fsck()


@pytest.mark.repo_files("laptop_macbook_pro.0",
                        "dir1/laptop_macbook_pro.1",
                        "dir1/dir2/laptop_macbook_pro.2",
                        "dir1/dir2/dir3/laptop_macbook_pro.3",
                        "dir1/dir2/dir3/dir4/laptop_macbook_pro.4",
                        "dir1/dir2/dir3/dir4/dir5/laptop_macbook_pro.5",
                        "dir1/dir2/dir3/dir4/dir5/dir6/laptop_macbook_pro.6",)
def test_unset_depth_flag(repo: Repo) -> None:
    """
    Test correct behavior for `onyo set --depth N KEY=VALUE <assets>` for
    different values for `--depth N`:
    - correct error for values smaller then 0
    - changing correct just assets in same dir for --depth 0
    - changing assets until sub-dir is --depth N deep
    - changing all assets if --depth is deeper then deepest sub-directory
      without error (e.g. deepest folder is 6, but --depth 8 is called)
    """
    set_values = "key=value"
    key = "key"
    # first, set values for the complete repository, so that there is something
    # to `onyo unset`
    ret = subprocess.run(['onyo', 'set', set_values], input='y', capture_output=True, text=True)

    # try `onyo unset --depth` for different values. Always discards changes,
    # and just checks if the output is the correct one.
    ret = subprocess.run(['onyo', 'unset', '--depth', '-1', key], capture_output=True, text=True)
    # verify output for invalid --depth
    assert not ret.stdout
    assert "depth values must be positive, but is -1" in ret.stderr
    assert ret.returncode == 1
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '0', key], input='n', capture_output=True, text=True)
    # verify output for --depth 0
    assert "laptop_macbook_pro.0" in ret.stdout
    assert f"-{key}" in ret.stdout
    assert "dir1/laptop_macbook_pro.1" not in ret.stdout
    # I think a value of zero should be allowed without error. It has no
    # additional functionality, but is logically consistent, and might help
    # while scripting with onyo.
    assert "depth values must be positive" not in ret.stderr
    assert ret.returncode == 0
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '1', key], input='n', capture_output=True, text=True)
    # verify output for --depth 1
    assert "laptop_macbook_pro.0" in ret.stdout
    assert ret.stdout.count(f"-{key}") == 2
    assert "dir1/laptop_macbook_pro.1" in ret.stdout
    assert "dir1/dir2/laptop_macbook_pro.2" not in ret.stdout
    assert "--depth must be bigger than 0" not in ret.stderr
    assert ret.returncode == 0
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '3', key], input='n', capture_output=True, text=True)
    # verify output for --depth 3
    assert "laptop_macbook_pro.0" in ret.stdout
    assert "dir1/laptop_macbook_pro.1" in ret.stdout
    assert "dir1/dir2/laptop_macbook_pro.2" in ret.stdout
    assert "dir1/dir2/dir3/laptop_macbook_pro.3" in ret.stdout
    assert "dir1/dir2/dir3/dir4/laptop_macbook_pro.4" not in ret.stdout
    assert ret.stdout.count(f"-{key}") == 4
    assert ret.returncode == 0
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '6', key], input='n', capture_output=True, text=True)
    # verify output for --depth 6 (maximum depth) contains all files
    assert "laptop_macbook_pro.0" in ret.stdout
    assert "dir1/laptop_macbook_pro.1" in ret.stdout
    assert "dir1/dir2/laptop_macbook_pro.2" in ret.stdout
    assert "dir1/dir2/dir3/laptop_macbook_pro.3" in ret.stdout
    assert "dir1/dir2/dir3/dir4/laptop_macbook_pro.4" in ret.stdout
    assert "dir1/dir2/dir3/dir4/dir5/laptop_macbook_pro.5" in ret.stdout
    assert "dir1/dir2/dir3/dir4/dir5/dir6/laptop_macbook_pro.6" in ret.stdout
    assert ret.stdout.count(f"-{key}") == len(repo.assets)
    assert ret.returncode == 0
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '10', key], input='n', capture_output=True, text=True)
    # verify output for --depth bigger then folder depth without error
    assert "laptop_macbook_pro.0" in ret.stdout
    assert "dir1/laptop_macbook_pro.1" in ret.stdout
    assert "dir1/dir2/laptop_macbook_pro.2" in ret.stdout
    assert "dir1/dir2/dir3/laptop_macbook_pro.3" in ret.stdout
    assert "dir1/dir2/dir3/dir4/laptop_macbook_pro.4" in ret.stdout
    assert "dir1/dir2/dir3/dir4/dir5/laptop_macbook_pro.5" in ret.stdout
    assert "dir1/dir2/dir3/dir4/dir5/dir6/laptop_macbook_pro.6" in ret.stdout
    assert ret.stdout.count(f"-{key}") == len(repo.assets)
    assert ret.returncode == 0
    repo.fsck()


name_fields = ["type",
               "make",
               "model",
               "serial",
               "key,type"]
@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('name_field', name_fields)
def test_error_unset_name_fields(repo: Repo, asset: str, name_field: str) -> None:
    """
    Test that `onyo unset KEY <asset>` throws the correct error without printing
    the usual information (e.g. diff output), when called with a KEY that is a
    name field (type, make, model or/and serial number), not a content field.
    """
    ret = subprocess.run(['onyo', 'unset', name_field, asset], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "Can't unset pseudo keys (name fields are required)." in ret.stderr
    assert ret.returncode == 1

    # verify state of repo is clean
    repo.fsck()
