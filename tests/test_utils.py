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
    assert utils.get_config_value('onyo.test.get-git', onyo_root) == 'get-git-test'


def test_get_config_value_onyo(helpers):
    ret = subprocess.run(["onyo", "config", "onyo.test.get-onyo", "get-onyo-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert helpers.string_in_file('get-onyo =', '.onyo/config')
    assert helpers.string_in_file('= get-onyo-test', '.onyo/config')

    onyo_root = './'
    assert utils.get_config_value('onyo.test.get-onyo', onyo_root) == 'get-onyo-test'


def test_get_editor_git():
    """
    Get the editor from git settings.
    """
    # set the editor
    ret = subprocess.run(["git", "config", "onyo.core.editor", 'vi'],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    onyo_root = './'
    assert utils.get_editor(onyo_root) == 'vi'

    # cleanup
    ret = subprocess.run(["git", "config", "--unset", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert ret.returncode == 0


def test_get_editor_onyo():
    """
    Get the editor from onyo settings.
    """
    # set the editor
    ret = subprocess.run(["onyo", "config", "onyo.core.editor", 'vi'],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    onyo_root = './'
    assert utils.get_editor(onyo_root) == 'vi'

    # cleanup
    ret = subprocess.run(["onyo", "config", "--unset", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert ret.returncode == 0


def test_get_config_value_envvar(helpers):
    """
    Get the editor from $EDITOR.
    """
    # verify that onyo.core.editor is not set
    ret = subprocess.run(["git", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout
    ret = subprocess.run(["onyo", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout

    os.environ['EDITOR'] = 'vi'
    onyo_root = './'
    assert utils.get_editor(onyo_root) == 'vi'


def test_get_editor_fallback():
    """
    When no editor is set, nano should be the fallback.
    """
    # verify that onyo.core.editor is not set
    ret = subprocess.run(["git", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout
    ret = subprocess.run(["onyo", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout

    onyo_root = './'
    assert utils.get_editor(onyo_root) == 'nano'


def test_get_editor_precedence():
    """
    The order of precedence should be git > onyo > $EDITOR.
    """
    # set for git
    ret = subprocess.run(["git", "config", "onyo.core.editor", 'first'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    # set for onyo
    ret = subprocess.run(["onyo", "config", "onyo.core.editor", 'second'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    # set $EDITOR
    os.environ['EDITOR'] = 'third'

    # git should win
    onyo_root = './'
    assert utils.get_editor(onyo_root) == 'first'

    # onyo should win
    ret = subprocess.run(["git", "config", '--unset', "onyo.core.editor"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert utils.get_editor(onyo_root) == 'second'

    # $EDITOR is all that's left
    ret = subprocess.run(["onyo", "config", '--unset', "onyo.core.editor"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert utils.get_editor(onyo_root) == 'third'
