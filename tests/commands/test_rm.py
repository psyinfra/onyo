import os
import subprocess
from pathlib import Path


def test_rm_flags(helpers):
    dirs = []
    files = ['a', 'b', 'c']

    # setup
    helpers.populate_repo('flags', dirs, files)
    os.chdir('flags')

    # --quiet (requires --yes)
    ret = subprocess.run(['onyo', 'rm', '--quiet', 'a'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert Path('a').is_file()
    assert not ret.stdout
    assert ret.stderr

    # --quiet with --yes success
    ret = subprocess.run(['onyo', 'rm', '--quiet', '--yes', 'b'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr
    assert not Path('b').is_file()

    # --quiet with --yes failure
    ret = subprocess.run(['onyo', 'rm', '--quiet', '--yes', 'does', 'not', 'exist'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr

    # --yes success
    ret = subprocess.run(['onyo', 'rm', '--yes', 'c'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('c').is_file()


def test_rm_cwd(helpers):
    dirs = ['simple']
    files = ['a']

    # setup
    helpers.populate_repo('cwd', dirs, files)
    os.chdir('cwd')

    # file
    ret = subprocess.run(['onyo', 'rm', '--yes', 'a'])
    assert ret.returncode == 0
    assert not Path('a').is_file()

    # directory
    ret = subprocess.run(['onyo', 'rm', '--yes', 'simple'])
    assert ret.returncode == 0
    assert not Path('simple').is_dir()


def test_rm_cwd_multiple(helpers):
    dirs = ['one', 'two', 'three']
    files = ['a', 'b', 'c', 'one/d', 'two/e', 'three/f']

    # setup
    helpers.populate_repo('cwd_multiple', dirs, files)
    os.chdir('cwd_multiple')

    # files
    ret = subprocess.run(['onyo', 'rm', '--yes', 'a', 'b', 'c'])
    assert ret.returncode == 0
    assert not Path('a').is_file()
    assert not Path('b').is_file()
    assert not Path('c').is_file()

    # directories
    ret = subprocess.run(['onyo', 'rm', '--yes', 'one', 'two', 'three'])
    assert ret.returncode == 0
    assert not Path('one').is_dir()
    assert not Path('two').is_dir()
    assert not Path('three').is_dir()


def test_rm_nested(helpers):
    dirs = ['one', 'two', 'three', 'r/e/c/u/r/s/i/v/e']
    files = ['a', 'b', 'c', 'one/d', 'two/e', 'three/f']

    # setup
    helpers.populate_repo('nested', dirs, files)
    os.chdir('nested')

    # files
    ret = subprocess.run(['onyo', 'rm', '--yes', 'one/d', 'two/e'])
    assert ret.returncode == 0
    assert not Path('one/d').is_file()
    assert not Path('two/e').is_file()
    assert Path('one').is_dir()
    assert Path('two').is_dir()

    # directories
    ret = subprocess.run(['onyo', 'rm', '--yes', 'r/e/c/u/r'])
    assert ret.returncode == 0
    assert not Path('r/e/c/u/r').is_dir()
    assert Path('r/e/c/u').is_dir()


def test_rm_spaces(helpers):
    dirs = ['s p a c e s', 's p a/c e s']
    files = ['s p a c e s/g', 's p a c e s/h', 's p a c e s/i',
             's p a/c e s/1 2', 's p a/c e s/3 4', 's p a/c e s/5 6']

    # setup
    helpers.populate_repo('spaces', dirs, files)
    os.chdir('spaces')

    # files
    ret = subprocess.run(['onyo', 'rm', '--yes', 's p a/c e s/1 2', 's p a/c e s/3 4'])
    assert ret.returncode == 0
    assert not Path('s p a/c e s/1 2').is_file()
    assert not Path('s p a/c e s/3 4').is_file()
    assert Path('s p a/c e s/5 6').is_file()
    assert Path('s p a/c e s/').is_dir()

    # directories
    ret = subprocess.run(['onyo', 'rm', '--yes', 's p a c e s', 's p a'])
    assert ret.returncode == 0
    assert not Path('s p a c e s').is_dir()
    assert not Path('s p a').is_dir()


def test_rm_same_target(helpers):
    dirs = ['simple']
    files = ['a']

    # setup
    helpers.populate_repo('same_target', dirs, files)
    os.chdir('same_target')

    # files
    ret = subprocess.run(['onyo', 'rm', '--yes', 'a', 'a', 'a'])
    assert ret.returncode == 0
    assert not Path('a').is_file()

    # directories
    ret = subprocess.run(['onyo', 'rm', '--yes', 'simple', 'simple'])
    assert ret.returncode == 0
    assert not Path('simple').is_dir()


def test_rm_overlap(helpers):
    dirs = ['overlap/one', 'overlap/two', 'overlap/three']
    files = []

    # setup
    helpers.populate_repo('overlap', dirs, files)
    os.chdir('overlap')

    ret = subprocess.run(['onyo', 'rm', '--yes', 'overlap/one', 'overlap', 'overlap/two'])
    assert ret.returncode == 0
    assert not Path('overlap').is_dir()


def test_rm_protected(helpers):
    dirs = ['simple']
    files = []

    # setup
    helpers.populate_repo('protected', dirs, files)
    os.chdir('protected')

    ret = subprocess.run(['onyo', 'rm', '--yes', '.onyo'])
    assert ret.returncode == 1
    assert Path('.onyo').is_dir()

    ret = subprocess.run(['onyo', 'rm', '--yes', '.git'])
    assert ret.returncode == 1
    assert Path('.git').is_dir()

    ret = subprocess.run(['onyo', 'rm', '--yes', 'simple/.anchor'])
    assert ret.returncode == 1
    assert Path('simple/.anchor').is_file()
