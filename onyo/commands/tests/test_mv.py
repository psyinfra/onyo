import subprocess
from pathlib import Path

from onyo.lib import OnyoRepo
import pytest

# These tests focus on functionality specific to the CLI for `onyo mv`.
# Tests located in this file should not duplicate those testing `OnyoRepo.mv()`
# directly.

assets = ['laptop_apple_macbookpro.0',
          'simple/laptop_apple_macbookpro.1',
          's p a/c e s/laptop_apple_macbookpro.2',
          'very/very/very/deep/spe\"c_ial\\ch_ar\'ac.teஞrs'
          ]


#
# FLAGS
#
@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_interactive_missing_y(repo: OnyoRepo) -> None:
    """
    Default mode is interactive. It requires a "y" to approve.
    """
    ret = subprocess.run(['onyo', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert ret.stderr

    assert Path('subdir/laptop_apple_macbook.abc123').exists()
    assert not Path('laptop_apple_macbook.abc123').exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_interactive_abort(repo: OnyoRepo) -> None:
    """
    Default mode is interactive. Provide the "n" to abort.
    """
    ret = subprocess.run(['onyo', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert not ret.stderr

    assert Path('subdir/laptop_apple_macbook.abc123').exists()
    assert not Path('laptop_apple_macbook.abc123').exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_interactive(repo: OnyoRepo) -> None:
    """
    Default mode is interactive. Provide the "y" to approve.
    """
    ret = subprocess.run(['onyo', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes? No discards all changes. (y/n) " in ret.stdout
    assert not ret.stderr

    assert not Path('subdir/laptop_apple_macbook.abc123').exists()
    assert Path('laptop_apple_macbook.abc123').exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_quiet_missing_yes(repo: OnyoRepo) -> None:
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', '--quiet', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr

    assert Path('subdir/laptop_apple_macbook.abc123').exists()
    assert not Path('laptop_apple_macbook.abc123').exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_quiet(repo: OnyoRepo) -> None:
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', '--yes', '--quiet', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr

    assert not Path('subdir/laptop_apple_macbook.abc123').exists()
    assert Path('laptop_apple_macbook.abc123').exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_yes(repo: OnyoRepo) -> None:
    """
    --yes removes any prompts and auto-approves the move.
    """
    ret = subprocess.run(['onyo', '--yes', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert "The following will be moved:" in ret.stdout
    assert "Save changes? No discards all changes. (y/n) " not in ret.stdout
    assert not ret.stderr

    assert not Path('subdir/laptop_apple_macbook.abc123').exists()
    assert Path('laptop_apple_macbook.abc123').exists()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_files(*assets)
@pytest.mark.repo_dirs("destination/")
@pytest.mark.parametrize('asset', assets)
def test_mv_message_flag(repo: OnyoRepo, asset: str) -> None:
    """
    Test that `onyo mv --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"
    ret = subprocess.run(['onyo', '--yes', 'mv', '--message', msg, asset,
                          "destination/"], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I', Path("destination") / Path(asset).name], capture_output=True, text=True)
    assert msg in ret.stdout
    assert repo.git.is_clean_worktree()
