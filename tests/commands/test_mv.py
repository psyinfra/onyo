import subprocess
from pathlib import Path
import pytest

# These tests focus on functionality specific to the CLI for `onyo mv`.
# Tests located in this file should not duplicate those testing `Repo.mv()`
# directly.

#
# FLAGS
#
@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_interactive_missing_y(repo):
    """
    Default mode is interactive. It requires a "y" to approve.
    """
    ret = subprocess.run(['onyo', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Move assets? (y/N) " in ret.stdout
    assert ret.stderr

    assert Path('subdir/laptop_apple_macbook.abc123').exists()
    assert not Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_interactive_abort(repo):
    """
    Default mode is interactive. Provide the "n" to abort.
    """
    ret = subprocess.run(['onyo', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Move assets? (y/N) " in ret.stdout
    assert not ret.stderr

    assert Path('subdir/laptop_apple_macbook.abc123').exists()
    assert not Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_interactive(repo):
    """
    Default mode is interactive. Provide the "y" to approve.
    """
    ret = subprocess.run(['onyo', 'mv', 'subdir/laptop_apple_macbook.abc123', './'], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Move assets? (y/N) " in ret.stdout
    assert not ret.stderr

    assert not Path('subdir/laptop_apple_macbook.abc123').exists()
    assert Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_quiet_missing_yes(repo):
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', 'mv', '--quiet', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr

    assert Path('subdir/laptop_apple_macbook.abc123').exists()
    assert not Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_quiet(repo):
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', 'mv', '--yes', '--quiet', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr

    assert not Path('subdir/laptop_apple_macbook.abc123').exists()
    assert Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('subdir/laptop_apple_macbook.abc123')
def test_mv_yes(repo):
    """
    --yes removes any prompts and auto-approves the move.
    """
    ret = subprocess.run(['onyo', 'mv', '--yes', 'subdir/laptop_apple_macbook.abc123', './'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert "The following will be moved:" in ret.stdout
    assert "Move assets? (y/N) " not in ret.stdout
    assert not ret.stderr

    assert not Path('subdir/laptop_apple_macbook.abc123').exists()
    assert Path('laptop_apple_macbook.abc123').exists()
