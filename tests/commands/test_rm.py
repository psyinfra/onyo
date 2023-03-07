import subprocess
from pathlib import Path

from onyo.lib import Repo
import pytest

# These tests focus on functionality specific to the CLI for `onyo rm`.
# Tests located in this file should not duplicate those testing `Repo.rm()`
# directly.

assets = ['laptop_apple_macbookpro.0',
          'simple/laptop_apple_macbookpro.1',
          's p a/c e s/laptop_apple_macbookpro.2',
          'very/very/very/deep/spe\"c_ial\\ch_ar\'ac.teஞrs'
          ]

#
# FLAGS
#
@pytest.mark.repo_files(*assets)
def test_rm_interactive_missing_y(repo: Repo) -> None:
    """
    Default mode is interactive. It requires a "y" to approve.
    """
    ret = subprocess.run(['onyo', 'rm', *assets], capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert ret.stderr

    # verify no changes were made and the repository is in a clean state
    for asset in assets:
        assert Path(asset).exists()
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_rm_interactive_abort(repo: Repo) -> None:
    """
    Default mode is interactive. Provide the "n" to abort.
    """
    ret = subprocess.run(['onyo', 'rm', *assets], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert not ret.stderr

    # verify no changes were made and the repository is in a clean state
    for asset in assets:
        assert Path(asset).exists()
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_rm_interactive(repo: Repo, asset: str) -> None:
    """
    Default mode is interactive. Provide the "y" to approve.
    """
    ret = subprocess.run(['onyo', 'rm', asset], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    assert not Path(asset).exists()
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_rm_quiet_missing_yes(repo: Repo) -> None:
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', 'rm', '--quiet', *assets], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr

    # verify no changes were made and the repository is in a clean state
    for asset in assets:
        assert Path(asset).exists()
    repo.fsck()


@pytest.mark.repo_files(*assets)
def test_rm_quiet(repo: Repo) -> None:
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', 'rm', '--yes', '--quiet', *assets], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    for asset in assets:
        assert not Path(asset).exists()
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_rm_yes(repo: Repo, asset: str) -> None:
    """
    --yes removes any prompts and auto-approves the deletion.
    """
    ret = subprocess.run(['onyo', 'rm', '--yes', asset], capture_output=True, text=True)
    assert ret.returncode == 0
    assert "The following will be deleted:" in ret.stdout
    assert "Remove assets? (y/N) " not in ret.stdout
    assert not ret.stderr

    # verify deleting was successful and the repository is in a clean state
    assert not Path(asset).exists()
    repo.fsck()


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_rm_message_flag(repo: Repo, asset: str) -> None:
    """
    Test that `onyo edit --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    ret = subprocess.run(['onyo', 'rm', '--yes', '--message', msg, asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I'], capture_output=True, text=True)
    assert msg in ret.stdout
    repo.fsck()
