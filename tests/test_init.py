import os
import subprocess
from pathlib import Path
import pytest
import git


@pytest.fixture(scope="function", autouse=True)
def change_test_dir(request, monkeypatch):
    test_dir = os.path.join(request.fspath.dirname, "sandbox/", "test_init/")
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(test_dir)


def fully_populated_dot_onyo(directory=''):
    """
    Assert whether a .onyo dir is fully populated.
    """
    dot_onyo = os.path.join(directory, '.onyo')

    if not os.path.isdir(dot_onyo) or \
       not os.path.isdir(dot_onyo + "/temp") or \
       not os.path.isdir(dot_onyo + "/templates") or \
       not os.path.isdir(dot_onyo + "/validation") or \
       not os.path.isfile(dot_onyo + "/config") or \
       not os.path.isfile(dot_onyo + "/.anchor") or \
       not os.path.isfile(dot_onyo + "/temp/.anchor") or \
       not os.path.isfile(dot_onyo + "/templates/.anchor") or \
       not os.path.isfile(dot_onyo + "/validation/.anchor"):
           return False  # noqa: E111, E117
    # TODO: assert that no unstaged or untracked under .onyo/

    return True


def test_cwd():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo()


def test_child_exist():
    Path('child_exist').mkdir()
    ret = subprocess.run(["onyo", "init", 'child_exist'])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo('child_exist')


def test_child_not_exist():
    ret = subprocess.run(["onyo", "init", 'child_not_exist'])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo('child_not_exist')


def test_child_with_spaces_not_exist():
    ret = subprocess.run(["onyo", "init", 'child with spaces not exist'])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo('child with spaces not exist')


def test_child_with_spaces_exist():
    Path('child with spaces exist').mkdir()
    ret = subprocess.run(["onyo", "init", 'child with spaces exist'])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo('child with spaces exist')


def test_fail_reinit_cwd():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 1
    # and nothing should be lost
    assert fully_populated_dot_onyo()


def test_fail_reinit_child():
    ret = subprocess.run(["onyo", "init", 'reinit_child'])
    assert ret.returncode == 0
    ret = subprocess.run(["onyo", "init", 'reinit_child'])
    assert ret.returncode == 1
    # and nothing should be lost
    assert fully_populated_dot_onyo('reinit_child')


# target dir that is too deep
def test_fail_missing_parent_dir():
    ret = subprocess.run(["onyo", "init", 'missing/parent/dir'])
    assert ret.returncode == 1
    assert not fully_populated_dot_onyo('missing/parent/dir')


# target dir that's already a git repo
def test_child_exist_with_git():
    Path('child_exist_with_git').mkdir()
    git.Repo.init('child_exist_with_git')

    ret = subprocess.run(["onyo", "init", 'child_exist_with_git'])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo('child_exist_with_git')


# target dir that contains non-git stuff
def test_child_with_cruft():
    Path('child_exist_with_cruft').mkdir()
    Path('child_exist_with_cruft/such_cruft.txt').touch()

    ret = subprocess.run(["onyo", "init", 'child_exist_with_cruft'])
    assert ret.returncode == 0
    assert fully_populated_dot_onyo('child_exist_with_cruft')
    # TODO: assert that child_exist_with_cruft/such_cruft.txt is not committed.
