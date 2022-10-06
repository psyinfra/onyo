import subprocess
from pathlib import Path


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


def test_simple_dir():
    ret = subprocess.run(["onyo", "mkdir", "simple/"])
    assert ret.returncode == 0
    assert anchored_dir('simple')


def test_dir_exists():
    ret = subprocess.run(["onyo", "mkdir", "simple/"])
    assert anchored_dir('simple')
    assert ret.returncode == 1


def test_dir_exists_as_file():
    ret = subprocess.run(["onyo", "mkdir", "simple/.anchor"])
    assert ret.returncode == 1


def test_dir_protected():
    # dir named .anchor
    ret = subprocess.run(["onyo", "mkdir", ".anchor"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert not Path('.anchor').exists()

    # dir named .git
    ret = subprocess.run(["onyo", "mkdir", "simple/.git"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert not Path('simple/.git').exists()

    # dir named .onyo
    ret = subprocess.run(["onyo", "mkdir", "simple/.onyo"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert not Path('simple/.onyo').exists()

    # dir inside of .onyo
    ret = subprocess.run(["onyo", "mkdir", ".onyo/nope"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert not Path('.onyo/nope').exists()


def test_recursive_dirs():
    ret = subprocess.run(["onyo", "mkdir", "r/e/c/u/r/s/i/v/e"])
    assert ret.returncode == 0
    assert anchored_dir('r')
    assert anchored_dir('r/e')
    assert anchored_dir('r/e/c')
    assert anchored_dir('r/e/c/u')
    assert anchored_dir('r/e/c/u/r')
    assert anchored_dir('r/e/c/u/r/s')
    assert anchored_dir('r/e/c/u/r/s/i')
    assert anchored_dir('r/e/c/u/r/s/i/v')
    assert anchored_dir('r/e/c/u/r/s/i/v/e')


def test_recursive_dir_exists():
    ret = subprocess.run(["onyo", "mkdir", "r/e/c/u/r/s/i/v/e"])
    assert ret.returncode == 1
    # they should be untouched
    assert anchored_dir('r')
    assert anchored_dir('r/e')
    assert anchored_dir('r/e/c')
    assert anchored_dir('r/e/c/u')
    assert anchored_dir('r/e/c/u/r')
    assert anchored_dir('r/e/c/u/r/s')
    assert anchored_dir('r/e/c/u/r/s/i')
    assert anchored_dir('r/e/c/u/r/s/i/v')
    assert anchored_dir('r/e/c/u/r/s/i/v/e')


def test_recursive_dir_exists_as_file():
    ret = subprocess.run(["onyo", "mkdir", "r/e/c/u/r/s/.anchor"])
    assert ret.returncode == 1
    # they should be untouched
    assert anchored_dir('r')
    assert anchored_dir('r/e')
    assert anchored_dir('r/e/c')
    assert anchored_dir('r/e/c/u')
    assert anchored_dir('r/e/c/u/r')
    assert anchored_dir('r/e/c/u/r/s')
    assert anchored_dir('r/e/c/u/r/s/i')
    assert anchored_dir('r/e/c/u/r/s/i/v')
    assert anchored_dir('r/e/c/u/r/s/i/v/e')


def test_dir_with_spaces():
    ret = subprocess.run(["onyo", "mkdir", "s p a c e s"])
    assert ret.returncode == 0
    assert anchored_dir('s p a c e s')
    for d in ['s', 'p', 'a', 'c', 'e', 's']:
        assert not Path(d).exists()

    ret = subprocess.run(["onyo", "mkdir", "s p a/c e s"])
    assert ret.returncode == 0
    assert anchored_dir('s p a')
    assert anchored_dir('s p a/c e s')
    for d in ['s', 'p', 'a', 'c', 'e', 's']:
        assert not Path(d).exists()


def test_dir_relative():
    ret = subprocess.run(["onyo", "mkdir", "simple/../relative"])
    assert ret.returncode == 0
    assert anchored_dir('relative')
    assert not Path('simple/\.\./relative').exists()


def test_multiple_dirs():
    ret = subprocess.run(["onyo", "mkdir", "one", "two", "three"])
    assert ret.returncode == 0
    assert anchored_dir('one')
    assert anchored_dir('two')
    assert anchored_dir('three')


def test_multiple_overlapping_dirs():
    ret = subprocess.run(["onyo", "mkdir", "overlap/one", "overlap/two", "overlap/three"])
    assert ret.returncode == 0
    assert anchored_dir('overlap/one')
    assert anchored_dir('overlap/two')
    assert anchored_dir('overlap/three')
