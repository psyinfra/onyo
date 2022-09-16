import os
import subprocess
from pathlib import Path
import pytest


@pytest.fixture(scope="function", autouse=True)
def change_test_dir(request, monkeypatch):
    test_dir = os.path.join(request.fspath.dirname, "sandbox/", "test_mkdir/")
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(test_dir)


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_simple_dir():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/"])
    assert ret.returncode == 0
    assert os.path.isdir( "da_dir/")  # noqa: E201
    assert os.path.isfile("da_dir/.anchor")


def test_dir_exists():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/"])
    assert ret.returncode == 1


def test_dir_exists_as_file():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/.anchor"])
    assert ret.returncode == 1


def test_recursive_dirs():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/a/b/c/d"])
    assert ret.returncode == 0
    assert os.path.isfile("da_dir/a/.anchor")
    assert os.path.isfile("da_dir/a/b/.anchor")
    assert os.path.isfile("da_dir/a/b/c/.anchor")
    assert os.path.isdir( "da_dir/a/b/c/d/")  # noqa: E201
    assert os.path.isfile("da_dir/a/b/c/d/.anchor")


def test_recursive_dir_exists():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/a/b/c/d"])
    assert ret.returncode == 1


def test_recursive_dir_exists_as_file():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/a/b/c/d/.anchor"])
    assert ret.returncode == 1


def test_dir_with_spaces():
    ret = subprocess.run(["onyo", "mkdir", "s p a c e s"])
    assert ret.returncode == 0
    assert os.path.isdir( "s p a c e s/")  # noqa: E201
    assert os.path.isfile("s p a c e s/.anchor")
    assert not os.path.exists("s")

    ret = subprocess.run(["onyo", "mkdir", "s p a/c e s"])
    assert ret.returncode == 0
    assert os.path.isdir( "s p a/")  # noqa: E201
    assert os.path.isfile("s p a/.anchor")
    assert os.path.isdir( "s p a/c e s/")  # noqa: E201
    assert os.path.isfile("s p a/c e s/.anchor")
    assert not os.path.exists("s")
    assert not os.path.exists("c")
    assert not os.path.exists("s p a/c")


def test_dir_relative():
    ret = subprocess.run(["onyo", "mkdir", "da_dir/../relative"])
    assert ret.returncode == 0
    assert os.path.isdir( "relative/")  # noqa: E201
    assert os.path.isfile("relative/.anchor")
    assert not os.path.exists("da_dir/\.\./relative")
