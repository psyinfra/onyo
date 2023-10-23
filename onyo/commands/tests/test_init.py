import os
import subprocess
from pathlib import Path

from onyo.lib import OnyoRepo


def fully_populated_dot_onyo(directory: str = '') -> bool:
    """
    Assert whether a .onyo dir is fully populated.
    """
    dot_onyo = Path(directory, '.onyo')

    if not Path(dot_onyo).is_dir() or \
       not Path(dot_onyo, "templates").is_dir() or \
       not Path(dot_onyo, "validation").is_dir() or \
       not Path(dot_onyo, "config").is_file() or \
       not Path(dot_onyo, ".anchor").is_file() or \
       not Path(dot_onyo, "templates/.anchor").is_file() or \
       not Path(dot_onyo, "validation/.anchor").is_file():
           return False  # noqa: E111, E117

    assert OnyoRepo(Path(directory)).git.is_clean_worktree()
    return True


def test_init_cwd(tmp_path: str) -> None:
    """
    Test that `onyo init` without a path argument uses the cwd to initialize a
    new onyo repository.
    """
    os.chdir(tmp_path)
    ret = subprocess.run(["onyo", "init"], capture_output=True, text=True)

    # verify output and that initializing the new repository was successful.
    assert "Initialized Onyo repository in" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0
    assert fully_populated_dot_onyo(tmp_path)
    repo = OnyoRepo(Path(tmp_path))
    assert repo.git.root == tmp_path
    assert repo.git.is_clean_worktree()


def test_init_with_path(tmp_path: str) -> None:
    """
    Test that `onyo init PATH` uses a provided path to initialize a new onyo
    repository.
    """
    repo_path = Path(tmp_path).resolve()
    ret = subprocess.run(["onyo", "init", repo_path], capture_output=True, text=True)

    # verify output and that initializing the new repository was successful.
    assert ret.returncode == 0
    assert fully_populated_dot_onyo(tmp_path)
    assert "Initialized Onyo repository in" in ret.stdout
    assert not ret.stderr
    repo = OnyoRepo(repo_path)
    assert repo.git.root == repo_path
    assert repo.git.is_clean_worktree()


def test_init_error_on_existing_repository(tmp_path: str) -> None:
    """
    Test that `onyo init PATH` errors correctly, when called on an existing
    repository.
    """
    repo_path = Path(tmp_path).resolve()
    ret = subprocess.run(["onyo", "init", repo_path], capture_output=True, text=True)
    ret = subprocess.run(["onyo", "init", repo_path], capture_output=True, text=True)

    # verify output and that double-initializing errors correctly, but the
    # repository stays in a valid state.
    assert ret.returncode == 1
    assert not ret.stdout
    assert "already exists." in ret.stderr

    assert fully_populated_dot_onyo(tmp_path)
    repo = OnyoRepo(repo_path)
    assert repo.git.root == repo_path
    assert repo.git.is_clean_worktree()
