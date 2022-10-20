import logging
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import Repo
import pytest


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_add_simple_str(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('simple-str').touch()
    repo.add('simple-str')
    assert Path('simple-str') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_simple_Path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('simple-Path').touch()
    repo.add(Path('simple-Path'))
    assert Path('simple-Path') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_list_str(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('list-one').touch()
    Path('list-two').touch()
    Path('list-three').touch()
    repo.add(['list-one', 'list-two', 'list-three'])
    assert Path('list-one') in repo.files_staged
    assert Path('list-two') in repo.files_staged
    assert Path('list-three') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_list_Path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('list-Path-one').touch()
    Path('list-Path-two').touch()
    Path('list-Path-three').touch()
    repo.add({Path('list-Path-one'), 'list-Path-two', Path('list-Path-three')})
    assert Path('list-Path-one') in repo.files_staged
    assert Path('list-Path-two') in repo.files_staged
    assert Path('list-Path-three') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_list_mixed(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('list-mix-one-str').touch()
    Path('list-mix-two-Path').touch()
    Path('list-mix-three-str').touch()
    repo.add(['list-mix-one-str', Path('list-mix-two-Path'), 'list-mix-three-str'])
    assert Path('list-mix-one-str') in repo.files_staged
    assert Path('list-mix-two-Path') in repo.files_staged
    assert Path('list-mix-three-str') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_set_str(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('set-one').touch()
    Path('set-two').touch()
    Path('set-three').touch()
    repo.add({'set-one', 'set-two', 'set-three'})
    assert Path('set-one') in repo.files_staged
    assert Path('set-two') in repo.files_staged
    assert Path('set-three') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_set_Path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('set-Path-one').touch()
    Path('set-Path-two').touch()
    Path('set-Path-three').touch()
    repo.add({Path('set-Path-one'), 'set-Path-two', Path('set-Path-three')})
    assert Path('set-Path-one') in repo.files_staged
    assert Path('set-Path-two') in repo.files_staged
    assert Path('set-Path-three') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_set_mixed(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('set-mix-one-Path').touch()
    Path('set-mix-two-str').touch()
    Path('set-mix-three-Path').touch()
    repo.add({Path('set-mix-one-Path'), 'set-mix-two-str', Path('set-mix-three-Path')})
    assert Path('set-mix-one-Path') in repo.files_staged
    assert Path('set-mix-two-str') in repo.files_staged
    assert Path('set-mix-three-Path') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_spaces_file(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('s p a c e s').touch()
    repo.add('s p a c e s')
    assert Path('s p a c e s') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_dir(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('dir-one').mkdir()
    Path('dir-two').mkdir()
    Path('dir-one/child-one-A').touch()
    Path('dir-one/child-one-B').touch()
    Path('dir-two/child-two-A').touch()
    Path('dir-two/child-two-B').touch()

    repo.add(['dir-one', 'dir-two'])
    assert Path('dir-one/child-one-A') in repo.files_staged
    assert Path('dir-one/child-one-B') in repo.files_staged
    assert Path('dir-two/child-two-A') in repo.files_staged
    assert Path('dir-two/child-two-B') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_spaces_dir(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('s p a/c e s').mkdir(parents=True)
    Path('s p a/c e s/child-A').touch()
    repo.add('s p a')
    assert Path('s p a/c e s/child-A') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_repeat(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('repeat-A').touch()
    Path('repeat-B').touch()
    Path('repeat-C').touch()
    repo.add(['repeat-A', 'repeat-B', 'repeat-A', 'repeat-C'])
    assert Path('repeat-A') in repo.files_staged
    assert Path('repeat-B') in repo.files_staged
    assert Path('repeat-C') in repo.files_staged

    # cleanup
    repo.commit('commit')


def test_add_unchanged(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('unchanged').touch()
    repo.add('unchanged')
    repo.commit('commit')

    # test
    repo.add('unchanged')


def test_add_missing(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    Path('missing-A').touch()
    Path('missing-C').touch()
    with pytest.raises(FileNotFoundError):
        repo.add(['missing-A', 'missing-B', 'missing-C'])
    assert Path('missing-A') not in repo.files_staged
    assert Path('missing-B') not in repo.files_staged
    assert Path('missing-C') not in repo.files_staged

    # no commit
