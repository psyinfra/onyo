import os
import subprocess
from pathlib import Path

import pytest

from onyo.lib.onyo import OnyoRepo

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

# Just a dummy asset specification for reuse throughout this file, represented as
# the respective part of the keys given to the `onyo new` call.
# TODO: This should probably become some kind of decorator/fixture/parametrization.
asset_spec = ['type=laptop', 'make=apple', 'model.name=macbookpro', 'serial=0']


@pytest.mark.repo_dirs(*directories)
@pytest.mark.parametrize('directory', directories)
def test_new(repo: OnyoRepo,
             directory: str) -> None:
    r"""Create an asset in a directory."""

    file_ = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', directory, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert file_ in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert Path(file_).exists()

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs(*directories)
def test_new_interactive(repo: OnyoRepo) -> None:
    r"""Create an asset when user responds "y" interactively."""

    file_ = f'{directories[0]}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', 'new', '--directory', directories[0], '--keys'] + asset_spec,
                         input='y', capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert "Create assets? (y/n) " in ret.stdout
    assert file_ in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert Path(file_).exists()

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    assert repo.git.is_clean_worktree()


def test_new_top_level(repo: OnyoRepo) -> None:
    r"""Create an asset in the repo root.

    This relies on CWD being the default for ``--directory`` and the ``repo``
    fixture ``cd``ing into the repo's root dir.
    """

    file_ = 'laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert file_ in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert Path(file_).exists()

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs(*directories)
def test_new_sub_dir_absolute_path(repo: OnyoRepo) -> None:
    r"""Create an asset outside of the CWD with absolute path."""

    # Change cwd to sub-directory
    cwd = repo.git.root / 'spe\"cial\\char\'acteஞrs'
    os.chdir(cwd)

    # build a path for the new asset as an absolute path
    subdir = repo.git.root / "just another path"
    file_ = subdir / "laptop_apple_macbookpro.0"

    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', subdir, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert str(file_) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs(*directories)
def test_new_sub_dir_relative_path(repo: OnyoRepo) -> None:
    r"""Create an asset outside of the CWD with relative path."""

    # Change cwd to sub-directory
    cwd = repo.git.root / 'r/e/c/u/r/s/i/v/e'
    os.chdir(cwd)

    # count levels until repo.git.root and build relative path with "../"
    var = "../" * (len(cwd.relative_to(repo.git.root).parts) - 1)

    # build a path for the new asset as a relative path
    subdir = Path(var) / "just another path"

    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', subdir, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert "just another path/laptop_apple_macbookpro.0" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all new assets exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs('overlap')  # to test sub-dir creation for existing dir
@pytest.mark.parametrize('directory', directories)
def test_folder_creation_with_new(repo: OnyoRepo, directory: str) -> None:
    r"""Automatically create parent directories."""

    asset = f"{directory}/laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', directory, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new assets exist and the repository is in a clean state
    repo_assets = repo.asset_paths
    assert (repo.git.root / asset).is_file()
    assert (repo.git.root / asset) in repo_assets
    assert len(repo_assets) == 1
    assert repo.git.is_clean_worktree()


def test_with_faux_serial_number(repo: OnyoRepo) -> None:
    r"""Create multiple assets with faux serials in multiple directories."""

    filename_prefix = "laptop_apple_macbookpro.faux"  # created asset files are expected to be this plus a random suffix

    num = 10
    assets = [[f"directory={d}", "serial=faux"] for d in directories for i in range(num)]
    cmd = ['onyo', '--yes', 'new', '--keys', 'type=laptop', 'make=apple', 'model.name=macbookpro']
    for a in assets:
        cmd += a
    ret = subprocess.run(cmd, capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    # file names are printed twice (diff and operations summary)
    assert ret.stdout.count(filename_prefix) == len(assets) * 2
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that all new assets exist and the repository is in a clean state
    assert len(repo.asset_paths) == len(directories) * num
    assert repo.git.is_clean_worktree()


def test_new_assets_in_multiple_directories_at_once(repo: OnyoRepo) -> None:
    r"""Create assets in multiple different directories."""

    assets = [f'{directory}/laptop_apple_macbookpro.{i}'
              for i, directory in enumerate(directories)]
    keys = ['--keys', 'type=laptop', 'make=apple', 'model.name=macbookpro']
    for i, directory in enumerate(directories):
        keys += [f'directory={directory}', f'serial={i}']
    ret = subprocess.run(['onyo', '--yes', 'new'] + keys,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
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
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_yes_flag(repo: OnyoRepo,
                  directory: str) -> None:
    r"""``onyo new --yes`` creates assets in different directories."""

    asset = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', directory, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
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
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_keys_flag(repo: OnyoRepo,
                   directory: str) -> None:
    r"""``onyo new --keys KEY=VALUE`` creates assets with contents added."""

    # set `key=value` for --keys, and asset name
    asset = f"{directory}/laptop_apple_macbookpro.0"
    key_values = "mode=keys_flag"

    # create asset with --keys
    ret = subprocess.run(
        ['onyo', '--yes', 'new', '--directory', directory, '--keys', key_values] + asset_spec,
        capture_output=True, text=True)

    # verify output
    assert "New assets:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that asset exists, the content is set, and the repository is clean
    assert (repo.git.root / asset) in repo.asset_paths
    assert 'mode: keys_flag' in Path.read_text(Path(repo.git.root / asset))
    assert repo.git.is_clean_worktree()


def test_error_keys_flag_mismatch_count(repo: OnyoRepo) -> None:
    r"""Error when repeated keys passed to ``--keys`` are not given the same number of times."""

    key_values = asset_spec + ['serial=1', 'mode=0', 'mode=1', 'mode=2']

    # create asset with --keys
    ret = subprocess.run(
        ['onyo', '--yes', 'new', '--keys'] + key_values,
        capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert "All keys given multiple times must be given the same number" in ret.stderr
    assert ret.returncode == 2

    # verify that no new assets were created and the repository stays clean
    assert len(repo.asset_paths) == 0
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_discard_changes(repo: OnyoRepo,
                         directory: str) -> None:
    r"""Discard and don't modify when user responds with "n"."""

    asset = f'{directory}/laptop_apple_macbookpro.0'
    ret = subprocess.run(['onyo', 'new', '--directory', directory, '--keys'] + asset_spec,
                         input='n', capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
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
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('protected_folder', [
    '.onyo',
    '.onyo/templates',
    '.onyo/validation',
    '.git',
    '.git/hooks',
    '.git/info'
])
def test_new_protected_folder(repo: OnyoRepo,
                              protected_folder: str) -> None:
    r"""Error when called on protected directories."""

    asset = f"{protected_folder}/laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', 'new', '--directory', protected_folder, '--keys'] + asset_spec,
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert f"{asset} is not a valid asset path" in ret.stderr

    # Verify that no asset was created and the repository is in a clean state
    assert not Path(asset).is_file()
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_new_with_flags_edit_keys_template(repo: OnyoRepo,
                                           directory: str) -> None:
    r"""All flags waterfall correctly."""

    # set editor, template, key=value and asset
    os.environ['EDITOR'] = "printf 'key: value' >>"
    template = repo.template_dir / "laptop.example"
    asset = Path(f"{directory}/laptop_apple_macbookpro.0")
    key_values = asset_spec + ["mode=keys"]

    # skip asset when asked for confirmation of the edited changes:
    ret = subprocess.run(['onyo', 'new', '--edit',
                          '--template', template, '--directory', directory, '--keys'] + key_values,
                         input='s',
                         capture_output=True, text=True)
    assert 'No new assets created.' in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # abort command when asked for confirmation of the edited changes:
    ret = subprocess.run(['onyo', 'new', '--edit',
                          '--template', template, '--directory', directory, '--keys'] + key_values,
                         input='a',
                         capture_output=True, text=True)
    assert "Accept changes?" in ret.stdout
    assert "interrupted" in ret.stderr
    assert ret.returncode == 1

    # create asset with --edit, --template and --keys
    ret = subprocess.run(['onyo', '--yes', 'new', '--edit',
                          '--template', template, '--directory', directory, '--keys'] + key_values,
                         capture_output=True, text=True)

    # verify output
    assert "Effective changes:" in ret.stdout
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
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_new_with_keys_overwrite_template(repo: OnyoRepo,
                                          directory: str) -> None:
    r"""Overwrite keys in a template."""

    # set asset, --template and --keys
    template = "laptop.example"
    asset = Path(f"{directory}/laptop_apple_macbookpro.0")
    key_values = asset_spec + ["RAM=16GB", "Size=24.2", "USB=3"]

    # create asset with --template and --keys
    ret = subprocess.run(['onyo', '--yes', 'new', '--template', template,
                          '--directory', directory, '--keys'] + key_values,
                         capture_output=True, text=True)

    # verify output
    assert "New assets:" in ret.stdout
    assert str(asset) in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that new asset exists and that the content is added.
    assert (repo.git.root / asset) in repo.asset_paths
    contents = Path.read_text(asset)

    # verify values from --keys are set
    assert "RAM: 16GB" in contents
    assert "Size: 24.2" in contents
    assert "USB: 3" in contents

    # verify that the repository is in a clean state
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
@pytest.mark.parametrize('variant', [
    ['spa ces', 'i n', 'as set', 'na me'],
    ['quotes', 'in', 'asset', 'na"me'],
    ['escapes', 'in', 'asset', 'na\\me'],
    ['lap\"top', 'appஞle', 'mac\\book\'pro', '0']
])
def test_with_special_characters(repo: OnyoRepo,
                                 directory: str,
                                 variant: str) -> None:
    r"""Test special characters."""

    asset = f'{directory}/{variant[0]}_{variant[1]}_{variant[2]}.{variant[3]}'
    keys = [f"type={variant[0]}", f"make={variant[1]}",
            f"model.name={variant[2]}", f"serial={variant[3]}"]
    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', directory, '--keys'] + keys,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 1
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files('laptop_apple_macbookpro.0')
@pytest.mark.parametrize('directory', directories)
def test_identical_asset_exists(repo: OnyoRepo,
                                directory: str) -> None:
    r"""Allow an asset identical to an existing one, but in a different directory."""

    asset = f"{directory}/laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', '--yes', 'new', '--directory', directory, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 2
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_two_identical_assets_in_input(repo: OnyoRepo,
                                       directory: str) -> None:
    r"""Create two identical assets in two different target directories."""

    asset = "laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', '--yes', 'new', '--keys'] + asset_spec + ["directory=.", f"directory={directory}"],
                         capture_output=True, text=True)

    # verify correct output
    assert "New assets:" in ret.stdout
    assert asset in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the new asset exists and the repository is in a clean state
    assert len(repo.asset_paths) == 2
    assert repo.git.is_clean_worktree()


@pytest.mark.parametrize('directory', directories)
def test_error_two_identical_assets_in_input(repo: OnyoRepo,
                                             directory: str) -> None:
    r"""Error when two assets result in identical name and location."""

    asset = "laptop_apple_macbookpro.0"
    ret = subprocess.run(['onyo', 'new', '--keys'] + asset_spec + [f"directory={directory}", f"directory={directory}"],
                         capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert asset in ret.stderr and "pending to be created" in ret.stderr
    assert ret.returncode == 1

    # verify that no new assets were created and the repository stays clean
    assert len(repo.asset_paths) == 0
    assert repo.git.is_clean_worktree()


def test_error_template_does_not_exist(repo: OnyoRepo) -> None:
    r"""Error when called with a non-existing template name."""

    no_template = "no_template"
    ret = subprocess.run(['onyo', 'new', '--template', no_template, '--keys'] + asset_spec,
                         capture_output=True, text=True)

    # verify correct error
    assert not ret.stdout
    assert "Template" in ret.stderr and "does not exist." in ret.stderr
    assert ret.returncode == 1

    # verify that no new assets were created and the repository stays clean
    assert len(repo.asset_paths) == 0
    assert repo.git.is_clean_worktree()


def test_conflicting_and_missing_arguments(repo: OnyoRepo) -> None:
    r"""Inform the user when arguments are missing or conflicting."""

    # error if `onyo new` gets neither temaplte, clone, edit, or keys
    ret = subprocess.run(['onyo', 'new'], capture_output=True, text=True)
    assert not ret.stdout
    assert "Key-value pairs or a template/clone-target must be given." in ret.stderr
    assert ret.returncode == 1

    # error on -d/--directory given multiple times
    ret = subprocess.run(['onyo', 'new', '--keys', 'make=some', 'model.name=other', 'type=different',
                          'serial=faux', '-d', 'some/where', '-d', 'else/where'],
                         capture_output=True, text=True)
    assert not ret.stdout
    assert "-d/--directory" in ret.stderr
    assert ret.returncode == 2

    # verify that the repository is in a clean state
    assert repo.git.is_clean_worktree()
