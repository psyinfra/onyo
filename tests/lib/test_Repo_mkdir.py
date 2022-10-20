import logging
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import Repo, OnyoProtectedPathError
import pytest


def anchored_dir(directory):
    """
    Returns True if a directory exists and contains an .anchor file.
    Otherwise it returns False.
    """
    if Path(directory).is_dir() and Path(directory, '.anchor').is_file():
        return True

    return False


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_mkdir_simple(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    repo.mkdir('simple')
    assert anchored_dir('simple')


def test_mkdir_recursive(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    repo.mkdir('r/e/c/u/r/s/i/v/e')
    assert anchored_dir('r')
    assert anchored_dir('r/e')
    assert anchored_dir('r/e/c')
    assert anchored_dir('r/e/c/u')
    assert anchored_dir('r/e/c/u/r')
    assert anchored_dir('r/e/c/u/r/s')
    assert anchored_dir('r/e/c/u/r/s/i')
    assert anchored_dir('r/e/c/u/r/s/i/v')
    assert anchored_dir('r/e/c/u/r/s/i/v/e')


def test_mkdir_spaces(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # single
    repo.mkdir('s p a c e s')
    assert anchored_dir('s p a c e s')

    # nested spaces
    repo.mkdir('s p a/c e s')
    assert anchored_dir('s p a/c e s')

    for d in [' ', 's', 'p', 'a', 'c', 'e', 's']:
        assert not Path(d).exists()
        assert not Path('s p a', d).exists()


def test_mkdir_relative(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    repo.mkdir('simple/../relative')
    assert anchored_dir('relative')


def test_mkdir_multiple_dirs(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    repo.mkdir(['one', 'two', 'three'])
    assert anchored_dir('one')
    assert anchored_dir('two')
    assert anchored_dir('three')


def test_mkdir_overlapping(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    repo.mkdir(['overlap/one', 'overlap/two', 'overlap/three'])
    assert anchored_dir('overlap/one')
    assert anchored_dir('overlap/two')
    assert anchored_dir('overlap/three')
    assert not Path('overlap/overlap').exists()
    assert not Path('overlap/one/overlap').exists()
    assert not Path('overlap/two/overlap').exists()
    assert not Path('overlap/three/overlap').exists()

    # test
    repo.mkdir(['double-o', 'double-o/one', 'double-o/two', 'double-o/three'])
    assert anchored_dir('double-o/one')
    assert anchored_dir('double-o/two')
    assert anchored_dir('double-o/three')
    assert not Path('double-o/double-o').exists()
    assert not Path('double-o/one/double-o').exists()
    assert not Path('double-o/two/double-o').exists()
    assert not Path('double-o/three/double-o').exists()


def test_mkdir_path(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # single
    repo.mkdir(Path('Path'))
    assert anchored_dir('Path')

    # multiple
    repo.mkdir([Path('Path-one'), Path('Path-two')])
    assert anchored_dir('Path-one')
    assert anchored_dir('Path-two')


def test_mkdir_path_str_mixed(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    repo.mkdir([Path('mixed-Path-one'), 'mixed-str-two'])
    assert anchored_dir('mixed-Path-one')
    assert anchored_dir('mixed-str-two')


def test_mkdir_protected(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # dir named .anchor
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir('protected/.anchor')
    assert not Path('protected/.anchor').exists()
    assert 'protected/.anchor' in caplog.text

    # dir named .git
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir('protected/.git')
    assert not Path('protected/.git').exists()
    assert 'protected/.git' in caplog.text

    # inside of .git
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir('.git/protected')
    assert not Path('.git/protected').exists()
    assert '.git/protected' in caplog.text

    # dir named .onyo
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir('protected/.onyo')
    assert not Path('protected/.onyo').exists()
    assert 'protected/.onyo' in caplog.text

    # inside of .onyo
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir('.onyo/protected')
    assert not Path('.onyo/protected').exists()
    assert '.onyo/protected' in caplog.text


def test_mkdir_protected_mixed(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # test
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir(['valid-one', 'protected/.anchor', 'valid-two'])
    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert not Path('protected/.anchor').exists()

    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir(['valid-one', '.onyo/protected', 'valid-two'])
    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert not Path('.onyo/protected').exists()

    # check logs
    assert 'valid-one' not in caplog.text
    assert 'valid-two' not in caplog.text
    assert 'protected/.anchor' in caplog.text
    assert '.onyo/protected' in caplog.text


def test_mkdir_exists_dir(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    repo.mkdir('exists-dir')

    # test
    with pytest.raises(FileExistsError):
        repo.mkdir('exists-dir')

    assert anchored_dir('exists-dir')
    assert not anchored_dir('exists-dir/exists-dir')

    # check log
    assert 'exists-dir' in caplog.text


def test_mkdir_exists_file(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    Path('exists-file').touch()
    repo.add('exists-file')
    repo.commit('add exists-file')

    # test
    with pytest.raises(FileExistsError):
        repo.mkdir('exists-file')

    assert not anchored_dir('exists-file')
    assert Path('exists-file').is_file()

    # check log
    assert 'exists-file' in caplog.text


def test_mkdir_exists_recursive_dir(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    repo.mkdir('exists-r-dir/r/e/c/u/r/s/i/v/e')

    # test
    with pytest.raises(FileExistsError):
        repo.mkdir('exists-r-dir/r/e/c/u/r/s/i/v/e')

    # they should be untouched
    assert anchored_dir('exists-r-dir/r')
    assert anchored_dir('exists-r-dir/r/e')
    assert anchored_dir('exists-r-dir/r/e/c')
    assert anchored_dir('exists-r-dir/r/e/c/u')
    assert anchored_dir('exists-r-dir/r/e/c/u/r')
    assert anchored_dir('exists-r-dir/r/e/c/u/r/s')
    assert anchored_dir('exists-r-dir/r/e/c/u/r/s/i')
    assert anchored_dir('exists-r-dir/r/e/c/u/r/s/i/v')
    assert anchored_dir('exists-r-dir/r/e/c/u/r/s/i/v/e')

    assert not anchored_dir('exists-r-dir/r/r')
    assert not anchored_dir('exists-r-dir/r/e/e')
    assert not anchored_dir('exists-r-dir/r/e/c/c')
    assert not anchored_dir('exists-r-dir/r/e/c/u/u')
    assert not anchored_dir('exists-r-dir/r/e/c/u/r/r')
    assert not anchored_dir('exists-r-dir/r/e/c/u/r/s/s')
    assert not anchored_dir('exists-r-dir/r/e/c/u/r/s/i/i')
    assert not anchored_dir('exists-r-dir/r/e/c/u/r/s/i/v/v')
    assert not anchored_dir('exists-r-dir/r/e/c/u/r/s/i/v/e/e')

    # check log
    assert 'exists-r-dir/r/e/c/u/r/s/i/v/e' in caplog.text


def test_mkdir_exists_recursive_file(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    repo.mkdir('exists-r-file/r/e/c/u/r/s/i/v/e')
    Path('exists-r-file/r/e/c/u/r/s/exists-r-file').touch()
    repo.add('exists-r-file/r/e/c/u/r/s/exists-r-file')
    repo.commit('add exists-r-file')

    # test
    with pytest.raises(FileExistsError):
        repo.mkdir('exists-r-file/r/e/c/u/r/s/exists-r-file')

    assert not anchored_dir('exists-r-file/r/e/c/u/r/s/exists-r-file')
    assert Path('exists-r-file/r/e/c/u/r/s/exists-r-file').is_file()

    # they should be untouched
    assert anchored_dir('exists-r-file/r')
    assert anchored_dir('exists-r-file/r/e')
    assert anchored_dir('exists-r-file/r/e/c')
    assert anchored_dir('exists-r-file/r/e/c/u')
    assert anchored_dir('exists-r-file/r/e/c/u/r')
    assert anchored_dir('exists-r-file/r/e/c/u/r/s')
    assert anchored_dir('exists-r-file/r/e/c/u/r/s/i')
    assert anchored_dir('exists-r-file/r/e/c/u/r/s/i/v')
    assert anchored_dir('exists-r-file/r/e/c/u/r/s/i/v/e')

    # check log
    assert 'exists-r-file/r/e/c/u/r/s/exists-r-file' in caplog.text


def test_mkdir_exists_mixed(caplog):
    caplog.set_level(logging.INFO, logger='onyo')
    repo = Repo('.')

    # setup
    repo.mkdir('exists-mixed')

    # test
    with pytest.raises(FileExistsError):
        repo.mkdir(['valid-one', 'exists-mixed', 'valid-two'])
    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert not Path('exists-mixed/valid-one').exists()
    assert not Path('exists-mixed/valid-two').exists()
    assert anchored_dir('exists-mixed')

    # check logs
    assert 'valid-one' not in caplog.text
    assert 'valid-two' not in caplog.text
    assert 'exists-mixed' in caplog.text
