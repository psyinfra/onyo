from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from onyo.lib.onyo import OnyoRepo

if TYPE_CHECKING:
    from typing import List

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro',
         'spe\"c_ial\\ch_ar\'ac.teஞrs']

directories = ['.',
               's p a c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'very/very/very/deep'
               ]

assets: List[str] = [f"{d}/{f}.{i}" for f in files for i, d in enumerate(directories)]


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_rm(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that `onyo rm ASSET` deletes assets and leaves the repository in a
    clean state.
    """
    ret = subprocess.run(['onyo', '--yes', 'rm', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed assets:" in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    assert not Path(asset).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
def test_rm_multiple_inputs(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo rm ASSET` deletes a list of assets all at once and leaves
    the repository in a clean state.
    """
    ret = subprocess.run(['onyo', '--yes', 'rm', *assets],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed assets:" in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    for asset in assets:
        assert not Path(asset).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('directory', directories[1:])  # do not use "." as dir
def test_rm_single_dirs_with_files(repo: OnyoRepo, directory: str) -> None:
    r"""
    Test that `onyo rm DIRECTORY` deletes directories successfully and leaves
    the repository in a clean state.
    """
    ret = subprocess.run(['onyo', '--yes', 'rm', '--recursive', directory],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed directories:" in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    assert not Path(directory).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
def test_rm_multiple_directories(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo rm DIRECTORY` deletes a list of directories all at once and
    leaves the repository in a clean state.
    """
    ret = subprocess.run(['onyo', '--yes', 'rm', '--recursive', *directories[1:]],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed directories:" in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    for directory in directories[1:]:
        assert not Path(directory).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs(*directories[1:])  # skip "." for directory creation
def test_rm_empty_directories(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo rm DIRECTORY` deletes empty directories and leaves the
    repository in a clean state.
    """
    ret = subprocess.run(['onyo', '--yes', 'rm', *directories[1:]],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed directories:" in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    for directory in directories[1:]:
        assert not Path(directory).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
def test_rm_interactive_missing_y(repo: OnyoRepo) -> None:
    r"""
    Default mode is interactive. It requires a "y" to approve.
    """
    ret = subprocess.run(['onyo', 'rm', *assets], capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert ret.stderr

    # verify no changes were made and the repository is in a clean state
    for asset in assets:
        assert Path(asset).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
def test_rm_interactive_abort(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo rm ASSET` does not delete any asset, when the user provides
    "n" as response in interactive mode.
    """
    ret = subprocess.run(['onyo', 'rm', *assets], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert not ret.stderr

    # verify no changes were made and the repository is in a clean state
    for asset in assets:
        assert Path(asset).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_rm_interactive(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that `onyo rm ASSET` deletes ASSET successfully, when the user provides
    "y" as the response in interactive mode.
    """
    ret = subprocess.run(['onyo', 'rm', asset], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    assert not Path(asset).exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_rm_message_flag(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that `onyo rm --message MESSAGE` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    ret = subprocess.run(['onyo', '--yes', 'rm', '--message', msg, asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I', '.'], capture_output=True, text=True)
    assert msg in ret.stdout
    assert repo.git.is_clean_worktree()
