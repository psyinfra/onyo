import subprocess
from pathlib import Path
import pytest

# These tests focus on functionality specific to the CLI for `onyo rm`.
# Tests located in this file should not duplicate those testing `Repo.rm()`
# directly.

#
# FLAGS
#
@pytest.mark.repo_files('laptop_apple_macbook.abc123')
def test_rm_interactive_missing_y(repo):
    """
    Default mode is interactive. It requires a "y" to approve.
    """
    ret = subprocess.run(['onyo', 'rm', 'laptop_apple_macbook.abc123'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Delete assets? (y/N) " in ret.stdout
    assert ret.stderr

    assert Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('laptop_apple_macbook.abc123')
def test_rm_interactive_abort(repo):
    """
    Default mode is interactive. Provide the "n" to abort.
    """
    ret = subprocess.run(['onyo', 'rm', 'laptop_apple_macbook.abc123'], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Delete assets? (y/N) " in ret.stdout
    assert not ret.stderr

    assert Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('laptop_apple_macbook.abc123')
def test_rm_interactive(repo):
    """
    Default mode is interactive. Provide the "y" to approve.
    """
    ret = subprocess.run(['onyo', 'rm', 'laptop_apple_macbook.abc123'], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Delete assets? (y/N) " in ret.stdout
    assert not ret.stderr

    assert not Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('laptop_apple_macbook.abc123')
def test_rm_quiet_missing_yes(repo):
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', 'rm', '--quiet', 'laptop_apple_macbook.abc123'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr

    assert Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('laptop_apple_macbook.abc123')
def test_rm_quiet(repo):
    """
    ``--quiet`` requires ``--yes``
    """
    ret = subprocess.run(['onyo', 'rm', '--yes', '--quiet', 'laptop_apple_macbook.abc123'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr

    assert not Path('laptop_apple_macbook.abc123').exists()


@pytest.mark.repo_files('laptop_apple_macbook.abc123')
def test_rm_yes(repo):
    """
    --yes removes any prompts and auto-approves the deletion.
    """
    ret = subprocess.run(['onyo', 'rm', '--yes', 'laptop_apple_macbook.abc123'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert "The following will be deleted:" in ret.stdout
    assert "Remove assets? (y/N) " not in ret.stdout
    assert not ret.stderr

    assert not Path('laptop_apple_macbook.abc123').exists()
