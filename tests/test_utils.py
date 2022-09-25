import os
import subprocess
from pathlib import Path
import pytest

from onyo import commands  # noqa: F401
from onyo import utils


@pytest.fixture(scope="function", autouse=True)
def change_test_dir(request, monkeypatch):
    test_dir = os.path.join(request.fspath.dirname, "sandbox/", "test_utils/")
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(test_dir)


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_get_config_value_git(helpers):
    ret = subprocess.run(["git", "config", "onyo.test.get-git", "get-git-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert helpers.string_in_file('get-git =', '.git/config')
    assert helpers.string_in_file('= get-git-test', '.git/config')

    onyo_root = './'
    value = utils.get_config_value('onyo.test.get-git', onyo_root)
    assert value == 'get-git-test'


def test_get_config_value_onyo(helpers):
    ret = subprocess.run(["onyo", "config", "onyo.test.get-onyo", "get-onyo-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert helpers.string_in_file('get-onyo =', '.onyo/config')
    assert helpers.string_in_file('= get-onyo-test', '.onyo/config')

    onyo_root = './'
    value = utils.get_config_value('onyo.test.get-onyo', onyo_root)
    assert value == 'get-onyo-test'
