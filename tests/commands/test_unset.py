import subprocess
from pathlib import Path

from onyo.lib import Repo
import pytest

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro']

directories = ['.',
               's p a c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'very/very/very/deep',
               ]

assets = [f"{d}/{f}.{i}" for f in files for i, d in enumerate(directories)]

content_dict = {"one_key": "one_value",
                "two_key": "two_value",
                "three_key": "three_value"}

content_str = "\n".join([f"{elem}: {content_dict.get(elem)}"
                         for elem in content_dict]) + "\n"

contents = [[x, content_str] for x in assets]

@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset KEY <asset>` removes keys from of assets.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    assert f"{key}: {content_dict.get(key)}" not in Path(asset).read_text()
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_interactive(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset KEY <asset>` removes keys from of assets.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--keys', key, '--path', asset], input='y', capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{key}: {content_dict.get(key)}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    assert f"{key}: {content_dict.get(key)}" not in Path(asset).read_text()
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_subset_of_keys(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset KEY <asset>` removes just the keys specified from
    assets with many other keys.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key, '--path', asset],
                         capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify the right key is removed and the others still exist, and that the
    # repository is still in a clean state
    asset_contents = Path(asset).read_text()
    assert f"{key}: {content_dict.get(key)}" not in asset_contents
    for k in list(content_dict.keys())[1:]:
        assert f"{k}: {content_dict.get(k)}" in asset_contents
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_unset_info_empty_asset(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --keys KEY --path ASSET` prints the correct info,
    when one of the KEYs does not exist, because the given asset is empty.
    """
    no_key = "non_existing"

    # test un-setting a non-existing key from an empty file
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', no_key,
                          '--path', asset], capture_output=True, text=True)

    # verify reaction of onyo
    assert "No assets containing the specified key(s) could be found. No assets updated." in ret.stdout
    assert f"Field {no_key} does not exist in " in ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_key_does_not_exist(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --keys KEY --path ASSET` prints the correct info,
    when one of the KEYs does not exist, but the asset is not empty.
    """
    no_key = "non_existing"

    # test un-setting a non-existing key from an empty file
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', no_key,
                          '--path', asset], capture_output=True, text=True)

    # verify reaction of onyo
    assert "No assets containing the specified key(s) could be found. No assets updated." in ret.stdout
    assert f"Field {no_key} does not exist in " in ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_contents(*contents)
def test_unset_multiple_assets(repo: Repo) -> None:
    """
    Test that `onyo unset --keys KEY --path ASSET` removes keys from of assets.
    """
    key = list(content_dict.keys())[0]

    # test unsetting keys for multiple assets:
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key, '--path', *assets], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    for asset in repo.assets:
        assert str(Path(asset)) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify changes, and the repository clean
    for asset in repo.assets:
        assert key not in Path(asset).read_text()
    repo.fsck()


non_existing_assets = [["single_non_existing.asset"],
                       ["simple/single_non_existing.asset"],
                       [assets[0], "single_non_existing.asset"]]
@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('no_assets', non_existing_assets)
def test_unset_error_non_existing_assets(repo: Repo, no_assets: list[str]) -> None:
    """
    Test that `onyo unset --keys KEY --path ASSET` errors correctly for
    non-existing assets on root, in directories, or if an invalid asset name is
    in a list of valid ones.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--keys', key, '--path', *no_assets],
                         capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths do not exist:" in ret.stderr
    assert ret.returncode == 1
    repo.fsck()


@pytest.mark.repo_contents(*contents)
def test_unset_with_dot(repo: Repo) -> None:
    """
    Test that when `onyo unset --keys KEY=VALUE --path .` is called from the
    repository root, onyo uses all assets in the completely repo recursively.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key,
                          '--path', "."], capture_output=True, text=True)

    assert "The following assets will be changed:" in ret.stdout
    # verify that output contains one line per asset
    assert ret.stdout.count(f"-{key}: {content_dict.get(key)}") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_contents(*contents)
def test_unset_without_path(repo: Repo) -> None:
    """
    Test that `onyo unset --keys KEY` without a given path argument selects all
    assets recursively.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key],
                         capture_output=True, text=True)

    # verify the output
    assert "The following assets will be changed:" in ret.stdout
    assert ret.stdout.count(f"-{key}: {content_dict.get(key)}") == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('directory', directories)
def test_unset_recursive_directories(repo: Repo, directory: str) -> None:
    """
    Test that `onyo unset --keys KEY --path DIRECTORY` updates contents of
    assets in DIRECTORY.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key, '--path', directory], capture_output=True, text=True)

    # verify changes, and the repository clean
    # TODO: update this after solving #259
    repo_assets = repo.assets
    for asset in [asset for asset in Path(directory).iterdir() if asset in repo_assets]:
        assert key not in Path(asset).read_text()
        assert f"-{key}: {content_dict.get(key)}" in ret.stdout
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_discard_changes_single_assets(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset` discards changes for assets successfully.
    """
    key = list(content_dict.keys())[0]
    # do an `onyo unset`, but answer "n" to discard the changes done by unset
    ret = subprocess.run(['onyo', 'unset', '--keys', key, '--path', asset], input='n', capture_output=True, text=True)
    assert f"-{key}: {content_dict.get(key)}" in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the key was not removed
    assert f"{key}: {content_dict.get(key)}" in Path(asset).read_text()
    repo.fsck()


@pytest.mark.repo_contents(*contents)
def test_unset_discard_changes_recursive(repo: Repo) -> None:
    """
    Test that `onyo unset` discards changes for all assets successfully.
    """
    key = list(content_dict.keys())[0]
    # call `unset`, but discard changes
    ret = subprocess.run(['onyo', 'unset', '--keys', key], input='n', capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert "Update assets? (y/n) " in ret.stdout
    assert "No assets updated." in ret.stdout
    assert ret.stdout.count(f"-{key}: {content_dict.get(key)}") == len(repo.assets)
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the removal was not written but discarded
    repo_assets = repo.assets
    for asset in repo_assets:
        assert f"{key}: {content_dict.get(key)}" in Path.read_text(asset)
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_yes_flag(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --yes KEY <asset>` updates assets without prompt.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--keys', key, '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following assets will be changed:" in ret.stdout
    assert str(Path(asset)) in ret.stdout
    assert f"-{key}" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # should not be asked with --yes flag
    assert "Update assets? (y/n) " not in ret.stdout

    # verify that the removal did happen, and the repository is still clean
    assert f"{key}" not in Path(asset).read_text()
    repo.fsck()


asset = 'simple/laptop_apple_macbookpro.0'
@pytest.mark.repo_files(asset)
def test_unset_quiet_without_yes_flag(repo: Repo) -> None:
    """
    Test that `onyo unset --quiet --keys KEY --path ASSET` errors correctly
    without the --yes flag.
    """
    ret = subprocess.run(['onyo', 'unset', '--quiet', '--keys', 'dummy_key',
                          '--path', asset], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The --quiet flag requires --yes." in ret.stderr
    assert ret.returncode == 1

    # verify that the repository is in a clean state
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_quiet_flag(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --quiet --yes --keys KEY --path ASSET` works correctly
    without output and user-response.
    """
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--quiet', '--keys', key,
                          '--path', asset], capture_output=True, text=True)
    # verify that output is completely empty
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that asset contents are updated
    assert f"{key}" not in Path(asset).read_text()

    # verify that the repository is in a clean state
    repo.fsck()


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_unset_message_flag(repo: Repo, asset: str) -> None:
    """
    Test that `onyo unset --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    key = list(content_dict.keys())[0]
    ret = subprocess.run(['onyo', 'unset', '--yes', '--message', msg,
                          '--keys', key, '--path', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I'], capture_output=True, text=True)
    assert msg in ret.stdout
    repo.fsck()


@pytest.mark.repo_contents(*contents)
def test_unset_dryrun_flag(repo: Repo) -> None:
    """
    Test that `onyo unset --dry-run --keys KEY --path ASSET` displays correct
    diff-output without actually changing any assets.
    """
    key = list(content_dict.keys())[0]
    # do a dry-run with unset, to check if the diff is correct without actually
    # changing an asset
    ret = subprocess.run(['onyo', 'unset', '--dry-run', '--keys', key,
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
        assert f"-{key}: {content_dict.get(key)}" in ret.stdout
        assert f"{key}: {content_dict.get(key)}" in Path(asset).read_text()

    # check that the repository is still clean
    repo.fsck()


depth_assets = ["laptop_macbook_pro.0",
                "dir1/laptop_macbook_pro.1",
                "dir1/dir2/laptop_macbook_pro.2",
                "dir1/dir2/dir3/laptop_macbook_pro.3",
                "dir1/dir2/dir3/dir4/laptop_macbook_pro.4",
                "dir1/dir2/dir3/dir4/dir5/laptop_macbook_pro.5",
                "dir1/dir2/dir3/dir4/dir5/dir6/laptop_macbook_pro.6"]
depth_contents = [[x, content_str] for x in depth_assets]
@pytest.mark.repo_contents(*depth_contents)
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
    key = list(content_dict.keys())[0]
    # try `onyo unset --depth` for different values. Always discards changes,
    # and just checks if the output is the correct one.
    ret = subprocess.run(['onyo', 'unset', '--depth', '-1', '--keys', key], capture_output=True, text=True)
    # verify output for invalid --depth
    assert not ret.stdout
    assert "depth values must be positive, but is -1" in ret.stderr
    assert ret.returncode == 1
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '0', '--keys', key], input='n', capture_output=True, text=True)
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

    ret = subprocess.run(['onyo', 'unset', '--depth', '1', '--keys', key], input='n', capture_output=True, text=True)
    # verify output for --depth 1
    assert "laptop_macbook_pro.0" in ret.stdout
    assert ret.stdout.count(f"-{key}") == 2
    assert "dir1/laptop_macbook_pro.1" in ret.stdout
    assert "dir1/dir2/laptop_macbook_pro.2" not in ret.stdout
    assert "--depth must be bigger than 0" not in ret.stderr
    assert ret.returncode == 0
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '3', '--keys', key], input='n', capture_output=True, text=True)
    # verify output for --depth 3
    assert "laptop_macbook_pro.0" in ret.stdout
    assert "dir1/laptop_macbook_pro.1" in ret.stdout
    assert "dir1/dir2/laptop_macbook_pro.2" in ret.stdout
    assert "dir1/dir2/dir3/laptop_macbook_pro.3" in ret.stdout
    assert "dir1/dir2/dir3/dir4/laptop_macbook_pro.4" not in ret.stdout
    assert ret.stdout.count(f"-{key}") == 4
    assert ret.returncode == 0
    repo.fsck()

    ret = subprocess.run(['onyo', 'unset', '--depth', '6', '--keys', key], input='n', capture_output=True, text=True)
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

    ret = subprocess.run(['onyo', 'unset', '--depth', '10', '--keys', key], input='n', capture_output=True, text=True)
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


name_fields = [["type"],
               ["make"],
               ["model"],
               ["serial"],
               ["one", "type"]]
@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
@pytest.mark.parametrize('name_field', name_fields)
def test_error_unset_name_fields(repo: Repo, asset: str, name_field: list[str]) -> None:
    """
    Test that `onyo unset KEY <asset>` throws the correct error without printing
    the usual information (e.g. diff output), when called with a KEY that is a
    name field (type, make, model or/and serial number), not a content field.
    """
    ret = subprocess.run(['onyo', 'unset', '--keys', *name_field, '--path', asset], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "Can't unset pseudo keys (name fields are required)." in ret.stderr
    assert ret.returncode == 1

    # verify state of repo is clean
    repo.fsck()
