import os
import subprocess
from pathlib import Path
import pytest


@pytest.fixture(scope="function", autouse=True)
def change_test_dir(request, monkeypatch):
    test_dir = os.path.join(request.fspath.dirname, "sandbox/", "test_config/")
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(test_dir)


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_config_set(helpers):
    ret = subprocess.run(["onyo", "config", "onyo.test.set", "set-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr
    assert helpers.string_in_file('set =', '.onyo/config')
    assert helpers.string_in_file('= set-test', '.onyo/config')


def test_config_get_onyo(helpers):
    # set
    ret = subprocess.run(["onyo", "config", "onyo.test.get-onyo", "get-onyo-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert helpers.string_in_file('get-onyo =', '.onyo/config')
    assert helpers.string_in_file('= get-onyo-test', '.onyo/config')

    # get
    ret = subprocess.run(["onyo", "config", "--get", "onyo.test.get-onyo"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout == 'get-onyo-test\n'
    assert not ret.stderr


# onyo should not alter git config's output (newline, etc)
def test_config_get_pristine(helpers):
    ret = subprocess.run(["onyo", "config", "onyo.test.get-pristine", "get-pristine-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert helpers.string_in_file('get-pristine =', '.onyo/config')
    assert helpers.string_in_file('= get-pristine-test', '.onyo/config')

    # git config's output
    ret = subprocess.run(["git", "config", "-f", ".onyo/config", "onyo.test.get-pristine"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout == 'get-pristine-test\n'
    git_config_output = ret.stdout

    # onyo config's output
    ret = subprocess.run(["onyo", "config", "--get", "onyo.test.get-pristine"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout == 'get-pristine-test\n'

    assert ret.stdout == git_config_output


def test_config_get_empty(helpers):
    assert not helpers.string_in_file('onyo.test.not-exist', '.onyo/config')

    ret = subprocess.run(["onyo", "config", "--get", "onyo.test.not-exist"],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert not ret.stderr


def test_config_unset(helpers):
    # set
    ret = subprocess.run(["onyo", "config", "onyo.test.unset", "unset-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert helpers.string_in_file('unset =', '.onyo/config')
    assert helpers.string_in_file('= unset-test', '.onyo/config')

    # unset
    ret = subprocess.run(["onyo", "config", "--unset", "onyo.test.unset"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr
    assert not helpers.string_in_file('unset =', '.onyo/config')
    assert not helpers.string_in_file('= unset-test', '.onyo/config')

    # get
    ret = subprocess.run(["onyo", "config", "--get", "onyo.test.unset"],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert not ret.stderr


def test_config_help():
    """
    `onyo config --help` is shown and not `git config --help`.
    """
    for flag in ['-h', '--help']:
        ret = subprocess.run(["onyo", "config", flag],
                             capture_output=True, text=True)
        assert ret.returncode == 0
        assert 'onyo' in ret.stdout
        assert not ret.stderr


def test_config_bubble_retcode(helpers):
    """
    Bubble up git-config's retcodes.
    According to the git config manpage, attempting to unset an option which
    does not exist exits with "5".
    """
    assert not helpers.string_in_file('onyo.test.not-exist', '.onyo/config')

    ret = subprocess.run(["onyo", "config", "--unset", "onyo.test.not-exist"],
                         capture_output=True, text=True)
    assert ret.returncode == 5


def test_config_bubble_stderr():
    """
    Bubble up git-config printing to stderr.
    """
    ret = subprocess.run(["onyo", "config", "--invalid-flag-oopsies", "such-an-oops"],
                         capture_output=True, text=True)
    assert ret.returncode == 129
    assert not ret.stdout
    assert ret.stderr