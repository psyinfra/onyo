import os
import subprocess
from pathlib import Path

from onyo.lib import OnyoRepo
from onyo.lib.commands import fsck
import pytest


prepared_tsvs = Path(__file__).parent / "tables"
directories = ['simple',
               's p a c e s',
               's p a/c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'overlap/three',
               'spe\"cial\\char\'acteஞrs',
               'very/very/very/deep'
               ]


@pytest.mark.repo_dirs(*directories)
@pytest.mark.parametrize('directory', directories)
def test_new(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new` can create an asset in different directories.
    """
    file_ = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', file_],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert file_ in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert Path(file_).exists()

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


@pytest.mark.repo_dirs(*directories)
def test_new_interactive(repo: OnyoRepo) -> None:
    """
    Test that `onyo new` can create an asset in different directories when given
    'y' as input in the dialog, instead of using the flag '--yes'.
    """
    file_ = f'{directories[0]}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', 'new', '--path', file_],
                         input='y', capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert "Create assets? (y/n) " in ret.stdout
    assert file_ in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert Path(file_).exists()

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


def test_new_top_level(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --path <path>` can create an asset on the top level of
    the repository.
    """
    file_ = 'laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', file_],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert file_ in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert Path(file_).exists()

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


@pytest.mark.repo_dirs(*directories)
def test_new_sub_dir_absolute_path(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --path <path>` can create an asset in sub-directories of
    the repository while the cwd is inside a different sub-directory.
    """
    # Change cwd to sub-directory
    cwd = repo.git.root / 'spe\"cial\\char\'acteஞrs'
    os.chdir(cwd)

    # build a path for the new asset as an absolute path
    file_ = repo.git.root / "just another path" / "laptop_apple_macbookpro.0"

    ret = subprocess.run(['onyo', '--yes', 'new', '--path', file_],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert str(file_) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


@pytest.mark.repo_dirs(*directories)
def test_new_sub_dir_relative_path(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --path <path>` can create an asset in sub-directories of
    the repository while the cwd is inside a different sub-directory with a
    relative path.
    """
    # Change cwd to sub-directory
    cwd = repo.git.root / 'r/e/c/u/r/s/i/v/e'
    os.chdir(cwd)

    # count levels until repo.git.root and build relative path with "../"
    var = "../" * (len(cwd.relative_to(repo.git.root).parts) - 1)

    # build a path for the new asset as a relative path
    file_ = Path(var, "just another path", "laptop_apple_macbookpro.0")

    ret = subprocess.run(['onyo', '--yes', 'new', '--path', file_],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert "just another path/laptop_apple_macbookpro.0" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all new assets exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


@pytest.mark.repo_dirs('overlap')  # to test sub-dir creation for existing dir
@pytest.mark.parametrize('directory', directories)
def test_folder_creation_with_new(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new` can create new folders for assets.
    Tests that folders are created when a sub-folder already exist, too, through
    existing dir 'overlap'.
    """
    asset = f"{directory}/laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', asset],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new assets exist and the repository is in a clean state
    repo_assets = repo.asset_paths
    assert (repo.git.root / asset).is_file()
    assert (repo.git.root / asset) in repo_assets
    assert len(repo_assets) == 1
    fsck(repo)


def test_with_faux_serial_number(repo: OnyoRepo) -> None:
    """
    Test that `onyo new` can create multiple assets with faux serial numbers in
    the multiple directories at once.
    """
    file_ = "laptop_apple_macbookpro.faux"
    num = 10
    assets = [f"{d}/{file_}" for d in directories for i in range(0, num)]
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', *assets],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert ret.stdout.count(file_) == len(assets)
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all new assets exist and the repository is in a clean state
    assert len(repo.asset_paths) == len(directories) * num
    fsck(repo)


def test_new_assets_in_multiple_directories_at_once(repo: OnyoRepo) -> None:
    """
    Test that `onyo new` cat create new assets in multiple different
    directories in one call.
    """
    assets = [f'{directory}/laptop_apple_macbookpro.{i}'
              for i, directory in enumerate(directories)]
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', *assets],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    for asset in assets:
        assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new assets exist and the repository is in a clean state
    repo_assets = repo.asset_paths
    for asset in assets:
        assert (repo.git.root / asset).is_file()
        assert (repo.git.root / asset) in repo_assets
    assert len(repo_assets) == len(directories)
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_yes_flag(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new --yes` creates assets in different directories.
    """
    asset = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', asset],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # should not be asked with the --yes flag
    assert "Create assets? (y/n) " not in ret.stdout

    # verify that the new asset exists and the repository is in a clean state
    assert Path(asset).is_file()
    repo_assets = repo.asset_paths
    assert (repo.git.root / asset) in repo_assets
    assert len(repo_assets) == 1
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_keys_flag(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new --keys KEY=VALUE` creates assets with contents added.
    """
    # set `key=value` for --keys, and asset name
    asset = f"{directory}/laptop_apple_macbookpro.0"
    key_values = "mode=keys_flag"

    # create asset with --keys
    ret = subprocess.run(['onyo', '--yes', 'new', '--keys', key_values,
                          '--path', asset], capture_output=True, text=True)

    # verify output
    assert "The following will be created:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that asset exists, the content is set, and the repository is clean
    assert (repo.git.root / asset) in repo.asset_paths
    assert 'mode: keys_flag' in Path.read_text(Path(repo.git.root / asset))
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_new_message_flag(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"

    asset = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--message', msg,
                          '--path', asset], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert msg in ret.stdout
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_discard_changes(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new` can discard new assets and the repository stays clean.
    """
    asset = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', 'new', '--path', asset],
                         input='n', capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert "Create assets? (y/n) " in ret.stdout
    assert asset in ret.stdout
    assert 'No new assets created.' in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that no new asset was created and the repository is still clean
    repo_assets = repo.asset_paths
    assert not (repo.git.root / asset).is_file()
    assert (repo.git.root / asset) not in repo_assets
    assert len(repo_assets) == 0
    fsck(repo)


@pytest.mark.parametrize('protected_folder', [
    '.onyo',
    '.onyo/templates',
    '.onyo/validation',
    '.git',
    '.git/hooks',
    '.git/info'
])
def test_new_protected_folder(repo: OnyoRepo, protected_folder: str) -> None:
    """
    Test that `onyo new` when called on protected folders errors correctly
    instead of creating an asset.
    """
    asset = f"{protected_folder}/laptop_apple_macbookpro.faux"
    ret = subprocess.run(['onyo', 'new', '--path', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "protected by onyo" in ret.stderr

    # Verify that no asset was created and the repository is in a clean state
    assert not Path(asset).is_file()
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_new_with_flags_edit_keys_template(repo: OnyoRepo, directory: str) -> None:
    """
    Test `onyo new --edit --keys KEY=VALUE --template <TEMPLATE>` works when
    called and all flags get executed together and modify the output correctly.
    """
    # set editor, template, key=value and asset
    os.environ['EDITOR'] = "printf 'key: value' >>"
    template = "laptop.example"
    asset = Path(f"{directory}/laptop_apple_macbookpro.0")
    key_values = "mode=keys"

    # create asset with --edit, --template and --keys
    ret = subprocess.run(['onyo', '--yes', 'new', '--edit',
                          '--template', template, '--keys', key_values,
                          '--path', str(asset)], capture_output=True, text=True)

    # verify output
    assert "The following will be created:" in ret.stdout
    assert str(asset) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that new asset exists and that the content is added.
    assert (repo.git.root / asset) in repo.asset_paths
    contents = Path.read_text(asset)
    # value from --template:
    assert 'RAM:' in contents
    # value from --edit:
    assert 'key: value' in contents
    # value from --keys:
    assert 'mode: keys' in contents

    # verify that the repository is in a clean state
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_new_with_keys_overwrite_template(repo: OnyoRepo, directory: str) -> None:
    """
    Test `onyo new --keys <KEY=VALUE> --template <TEMPLATE>` does overwrite the
    contents of <TEMPLATE> with <KEY=VALUE>
    """
    # set asset, --template and --keys
    template = "laptop.example"
    asset = Path(f"{directory}/laptop_apple_macbookpro.0")
    key_values = ["RAM=16GB", "Size=24.2", "USB=3"]

    # create asset with --template and --keys
    ret = subprocess.run(['onyo', '--yes', 'new', '--template', template,
                          '--keys', *key_values, '--path', str(asset)],
                         capture_output=True, text=True)

    # verify output
    assert "The following will be created:" in ret.stdout
    assert str(asset) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that new asset exists and that the content is added.
    assert (repo.git.root / asset) in repo.asset_paths
    contents = Path.read_text(asset)

    # verify values from --keys are set
    assert "RAM: 16GB" in contents
    assert "Size: '24.2'" in contents
    assert "USB: 3" in contents

    # verify that the repository is in a clean state
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
@pytest.mark.parametrize('variant', [
    'spa ces_i n_as set.na me',
    'quotes_in_asset.na"me',
    'escapes_in_asset.na\\me'
    'lap\"top_appஞle_mac\\book\'pro.0'
])
def test_with_special_characters(
        repo: OnyoRepo, directory: str, variant: str) -> None:
    """
    Test `onyo new` with names containing special characters.
    """
    asset = f'{directory}/{variant}'
    ret = subprocess.run(['onyo', '--yes', 'new', '--path', asset],
                         capture_output=True, text=True)

    # verify correct output
    assert "The following will be created:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


@pytest.mark.repo_files('laptop_apple_macbookpro.0')
@pytest.mark.parametrize('directory', directories)
def test_error_asset_exists_already(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new` errors in all possible locations when it is called with
    an asset name that already exists elsewhere in the directory.
    """
    asset = f"{directory}/laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', 'new', '--path', asset],
                         capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert f"Filename '{Path(asset).name}' already exists as" in ret.stderr
    assert ret.returncode == 1

    # verify that just the initial asset was created, but no new one, and the
    # repository is still in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


@pytest.mark.parametrize('directory', directories)
def test_error_two_identical_assets_in_input(
        repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo new` errors in all possible locations when it is called with
    the same asset name twice, in two different locations.
    """
    asset_a = "laptop_apple_macbookpro.0"
    asset_b = f"{directory}/{asset_a}"
    ret = subprocess.run(['onyo', 'new', '--path', asset_a, asset_b],
                         capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert f"Input contains multiple '{asset_a}'" in ret.stderr
    assert ret.returncode == 1

    # verify that no new assets were created and the repository stays clean
    assert len(repo.asset_paths) == 0
    fsck(repo)


def test_error_template_does_not_exist(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --template` errors when it is called with a non-existing
    template name.
    """
    asset = "laptop_apple_macbookpro.0"
    no_template = "no_template"
    ret = subprocess.run(['onyo', 'new', '--template', no_template,
                          '--path', asset], capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert "Template" in ret.stderr and "does not exist." in ret.stderr
    assert ret.returncode == 1

    # verify that no new assets were created and the repository stays clean
    assert len(repo.asset_paths) == 0
    fsck(repo)


@pytest.mark.repo_dirs('simple',
                       'overlap/one')
def test_tsv(repo: OnyoRepo) -> None:
    """
    Test `onyo new --tsv <table>` with a table containing the minimal set of
    columns to create assets: type, make, model, serial, directory.

    The table contains entries with and without faux serial numbers, spaces, and
    existing and non-existing folders.

    This is not meant to cover all test cases, but to verify that the flag
    actually does create assets and directories without error.
    """
    # select table for this test case
    table_path = prepared_tsvs / "table.tsv"
    assert table_path.is_file()

    # create assets with table
    ret = subprocess.run(['onyo', '--yes', 'new', "--tsv", table_path],
                         capture_output=True, text=True)
    assert not ret.stderr
    assert "The following will be created:" in ret.stdout
    assert ret.returncode == 0

    # verify that the new assets exist and the repository is in a clean state
    # TODO: open table and count rows for specific number?
    assert len(repo.asset_paths) > 0
    fsck(repo)


@pytest.mark.repo_dirs('simple',
                       'overlap/one')
def test_tsv_with_value_columns(repo: OnyoRepo) -> None:
    """
    Test `onyo new --tsv <table>` with a table containing a column with the age
    of the device and a group to which it belongs.
    """
    table_path = prepared_tsvs / "table_with_key_values.tsv"
    ret = subprocess.run(['onyo', '--yes', 'new', '--tsv', table_path],
                         capture_output=True, text=True)

    assert "The following will be created:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new assets exist, the contents are added, and the
    # repository is in a clean state
    repo_assets = repo.asset_paths
    assert len(repo_assets) > 0
    for asset in repo_assets:
        contents = Path.read_text(repo.git.root / asset)
        assert "group: " in contents
        assert "age: " in contents
    fsck(repo)


@pytest.mark.repo_dirs('simple',
                       'overlap/one')
def test_tsv_with_flags_template_keys_edit(repo: OnyoRepo) -> None:
    """
    Test `onyo new --tsv <table> --template <template> <key=value> --edit`
    with a table containing the minimal set of columns to create assets, a
    non-empty template, values to set with --keys, and an editor.
    """
    # select table, editor, --keys values and template
    table_path = prepared_tsvs / "table.tsv"
    os.environ['EDITOR'] = "printf 'key: value' >>"
    template = "laptop.example"
    key_values = "mode=keys"
    assert table_path.is_file()

    # create assets with table
    ret = subprocess.run(['onyo', '--yes', 'new', '--edit',
                          '--keys', key_values, '--tsv', table_path,
                          '--template', template],
                         capture_output=True, text=True)

    assert "The following will be created:" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new assets exist, the contents from different locations
    # are set and the repository is in a clean state
    assert len(repo.asset_paths) > 0
    for asset in repo.asset_paths:
        contents = Path.read_text(repo.git.root / asset)
        # from --template:
        assert "RAM:" in contents
        # from --edit:
        assert 'key: value' in contents
        # from --keys:
        assert 'mode: keys' in contents
    fsck(repo)


@pytest.mark.repo_dirs('simple',
                       'overlap/one')
def test_tsv_with_template_column(repo: OnyoRepo) -> None:
    """
    Test `onyo new --tsv <table>` with a table containing an additional column
    specifying the template to use.

    The table contains entries with and without faux serial numbers, spaces, and
    existing and non-existing folders, and the columns are in a different order.
    """
    table_path = prepared_tsvs / "table_with_template.tsv"
    assert table_path.is_file()

    # create assets with table
    ret = subprocess.run(['onyo', '--yes', 'new', '--tsv', table_path],
                         capture_output=True, text=True)
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new assets exist and the repository is in a clean state
    # TODO: open table and count rows for specific number?
    # TODO: check asset content to verify usage of templates
    assert len(repo.asset_paths) > 0
    fsck(repo)


def test_conflicting_and_missing_arguments(repo: OnyoRepo) -> None:
    """
    Onyo should inform the user with specific error messages when arguments are
    either missing or conflicting:
    - error if `onyo new` gets neither table nor asset names
    - error if `onyo new` with table and assets in CLI
    - error if both `--template` and 'template' column in tsv header are given
    - error if both `KEY=VALUE` and a column named `KEY` is given
    """
    table_path = prepared_tsvs / "table_with_template.tsv"
    assert table_path.is_file()

    # error if `onyo new` gets neither table nor asset names
    ret = subprocess.run(['onyo', 'new'], capture_output=True, text=True)
    assert not ret.stdout
    assert "Either asset(s) or a tsv file must be given." in ret.stderr
    assert ret.returncode == 1

    # error if `onyo new` is called with TSV and assets in CLI
    ret = subprocess.run(['onyo', 'new', "--tsv", table_path,
                          '--path', 'simple/laptop_apple_macbookpro.0'],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert "Can't have asset(s) and tsv file given." in ret.stderr
    assert ret.returncode == 1

    # error if both `--template` and 'template' column in tsv header are given
    ret = subprocess.run(['onyo', 'new', "--tsv", table_path,
                          "--template", "empty"],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert "Can't use --template and template column in tsv." in ret.stderr
    assert ret.returncode == 1

    # error if both `--keys KEY=VALUE` and a column named `KEY` is given
    table_path = prepared_tsvs / "table_with_key_values.tsv"
    ret = subprocess.run(['onyo', 'new', '--keys', 'group=a_group',
                          '--tsv', table_path], capture_output=True, text=True)
    assert not ret.stdout
    assert "Can't use --keys" in ret.stderr and "and have tsv column" in ret.stderr
    assert ret.returncode == 1

    # verify that the repository is in a clean state
    fsck(repo)


def test_tsv_errors(repo: OnyoRepo) -> None:
    """
    Test error behavior for `onyo new --tsv <TSV>`:
    - <TSV> does not exist
    - <TSV> exists, but is empty (no columns/header)
    - <TSV> contains 5 assets, but each misses one field
    - <TSV> has necessary columns but contains no assets
    """
    # <TSV> does not exist
    table = Path("non_existing_table.tsv")
    ret = subprocess.run(['onyo', 'new', '--tsv', table],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert f"{table} does not exist." in ret.stderr
    assert ret.returncode == 1

    # <TSV> exists, but is empty (no columns/header)
    table = prepared_tsvs / "error_empty_table.tsv"
    ret = subprocess.run(['onyo', 'new', "--tsv", table],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert "onyo new --tsv needs columns 'type', 'make', 'model', 'serial' and 'directory'." in ret.stderr
    assert ret.returncode == 1

    # <TSV> contains 5 assets, but each misses one field
    table = prepared_tsvs / "error_incomplete_rows.tsv"
    ret = subprocess.run(['onyo', 'new', "--tsv", table],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert "The fields 'type', 'make', 'model', 'serial' and 'directory' are required" in ret.stderr
    assert ret.returncode == 1

    # <TSV> has necessary columns but contains no assets
    table = prepared_tsvs / "error_empty_columns.tsv"
    ret = subprocess.run(['onyo', 'new', "--tsv", table],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert "No new assets given." in ret.stderr
    assert ret.returncode == 1

    # verify that the repository is in a clean state
    fsck(repo)


@pytest.mark.repo_files("laptop_apple_macbookpro.0")
def test_tsv_error_asset_exists_already(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --tsv` errors correctly when the table contains an
    asset name that already exists in the repository.
    """
    asset = "laptop_apple_macbookpro.0"
    table = prepared_tsvs / "table.tsv"
    assert table.is_file()
    ret = subprocess.run(['onyo', 'new', '--tsv', table], capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert f"Filename '{asset}' already exists as" in ret.stderr
    assert ret.returncode == 1

    # verify that (except the initial one) no new assets were created and the
    # repository stays in a clean state
    assert len(repo.asset_paths) == 1
    fsck(repo)


def test_tsv_error_identical_entries(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --tsv` errors when the table contains two assets with
    the same name (type, make, model and serial identical, but directories
    different).
    """
    table = prepared_tsvs / "error_identical_entries.tsv"
    assert table.is_file()
    ret = subprocess.run(['onyo', 'new', '--tsv', table],
                         capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert "Input contains multiple" in ret.stderr
    assert ret.returncode == 1

    # verify that no new assets were created and the repository is still clean
    assert len(repo.asset_paths) == 0
    fsck(repo)


def test_tsv_error_template_does_not_exist(repo: OnyoRepo) -> None:
    """
    Test that `onyo new --tsv` errors when the template column contains entries
    for which no template exist (e.g. typos).
    """
    table = prepared_tsvs / "error_template_does_not_exist.tsv"
    assert table.is_file()
    ret = subprocess.run(['onyo', 'new', '--tsv', table],
                         capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert "Template" in ret.stderr and "does not exist." in ret.stderr
    assert ret.returncode == 1

    # verify that no new assets were created and the repository is still clean
    assert len(repo.asset_paths) == 0
    fsck(repo)


@pytest.mark.parametrize('variant', [
    'laptop_apple_macbookpro_0',
    'lap top _ app le _ mac book pro_ 0',
    'laptop_ap.ple_macbookpro.0',
    'lap_top_apple_macbookpro.0',
    'laptop-apple-macbookpro.0',
    '_apple_macbookpro.0',
    'laptop__macbookpro.0',
    'laptop_apple_.0',
    'laptop_apple_macbookpro.'
])
def test_error_namescheme(repo: OnyoRepo, variant: str) -> None:
    """
    Test that `onyo new` prints correct errors for different invalid names:
    - '.' in another field as serial number
    - Additional '_' in one of the early fields
    - instead of '_' using '-' to divide fields
    """
    ret = subprocess.run(['onyo', 'new', '--path', variant],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert ret.returncode == 1
    assert "must be in the format '<type>_<make>_<model>.<serial>'" in ret.stderr

    # verify that no new assets were created and the repository state is clean
    assert len(repo.asset_paths) == 0
    fsck(repo)
