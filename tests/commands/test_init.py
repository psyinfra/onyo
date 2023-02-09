import os
import subprocess
from pathlib import Path


def fully_populated_dot_onyo(directory=''):
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
    # TODO: assert that no unstaged or untracked under .onyo/

    return True


def test_cwd(tmp_path):
    os.chdir(tmp_path)

    ret = subprocess.run(["onyo", "init"])

    assert ret.returncode == 0
    assert fully_populated_dot_onyo()


def test_explicit(tmp_path):
    repo_path = Path(tmp_path).resolve()
    ret = subprocess.run(["onyo", "init", repo_path])

    assert ret.returncode == 0
    assert fully_populated_dot_onyo()
