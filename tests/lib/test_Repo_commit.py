import logging
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import Repo
import pytest


def last_commit_message() -> str:
    ret = subprocess.run(['git', 'log', '-1', '--pretty=format:%B'],
                         capture_output=True, text=True)
    return ret.stdout


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_commit_str(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('str').touch()
    repo.add('str')

    # test
    repo.commit('single string')
    msg = last_commit_message()
    assert 'single string\n' == msg


def test_commit_int(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('int').touch()
    repo.add('int')

    # test
    repo.commit(525600)
    msg = last_commit_message()
    assert '525600\n' == msg


def test_commit_multi_str(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('multi-str').touch()
    repo.add('multi-str')

    # test
    repo.commit('multiple', 'strings', 'another')
    msg = last_commit_message()
    assert 'multiple\n\n' + 'strings\n\n' + 'another\n' == msg


def test_commit_multi_str_Path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('multi-str-Path').touch()
    repo.add('multi-str-Path')

    # test
    repo.commit('changed:', 'I HAVE REASONS', Path('multi-str-Path'))
    msg = last_commit_message()
    assert 'changed:\n\n' + 'I HAVE REASONS\n\n' + 'multi-str-Path\n' == msg


def test_commit_multi_str_list(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('multi-str-list').touch()
    repo.add('multi-str-list')

    # test
    repo.commit('changed:', 'I HAVE REASONS', ['one', 'two', 'three'])
    msg = last_commit_message()
    assert 'changed:\n\n' + 'I HAVE REASONS\n\n' + 'one\ntwo\nthree\n' == msg


def test_commit_multi_str_set(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('multi-str-set').touch()
    repo.add('multi-str-set')

    # test
    repo.commit('changed:', 'I HAVE REASONS', {'one', 'two', 'three'})
    msg = last_commit_message()
    assert 'changed:\n\n' + 'I HAVE REASONS\n\n' in msg
    # sets are unordered
    assert 'one\n' in msg
    assert 'two\n' in msg
    assert 'three\n' in msg


def test_commit_multi_str_list_Path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('multi-str-list-Path').touch()
    repo.add('multi-str-list-Path')

    # test
    repo.commit('changed:', 'I HAVE REASONS', [Path('one'), Path('two'), Path('three')])
    msg = last_commit_message()
    assert 'changed:\n\n' + 'I HAVE REASONS\n\n' + 'one\ntwo\nthree\n' == msg


def test_commit_multi_str_set_Path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('multi-str-set-Path').touch()
    repo.add('multi-str-set-Path')

    # test
    repo.commit('changed:', 'I HAVE REASONS', {Path('one'), Path('two'), Path('three')})
    msg = last_commit_message()
    assert 'changed:\n\n' + 'I HAVE REASONS\n\n' in msg
    # sets are unordered
    assert 'one\n' in msg
    assert 'two\n' in msg
    assert 'three\n' in msg


def test_commit_nothing(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    with pytest.raises(subprocess.CalledProcessError):
        repo.commit('We believe in nothing Lebowski!')

    msg = last_commit_message()
    assert 'We believe in nothing Lebowski!' not in msg
