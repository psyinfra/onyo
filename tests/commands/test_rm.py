import os
import subprocess
from pathlib import Path
from git import Repo


def populate_test_repo(path):
    create_dirs = ['simple',
                   's p a c e s',
                   's p a/c e s',
                   'r/e/c/u/r/s/i/v/e',
                   'relative',
                   'one',
                   'two',
                   'three',
                   'overlap/one',
                   'overlap/two',
                   'overlap/three'
                   ]

    ret = subprocess.run(['onyo', 'init', path])
    assert ret.returncode == 0

    # enter repo
    original_cwd = Path.cwd()
    os.chdir(path)

    # create dirs
    ret = subprocess.run(['onyo', 'mkdir'] + create_dirs)
    assert ret.returncode == 0

    # create files
    Path('a').touch()
    Path('b').touch()
    Path('c').touch()
    Path('one/d').touch()
    Path('two/e').touch()
    Path('three/f').touch()
    Path('s p a c e s/g').touch()
    Path('s p a c e s/h').touch()
    Path('s p a c e s/i').touch()
    Path('s p a/c e s/1 2').touch()
    Path('s p a/c e s/3 4').touch()
    Path('s p a/c e s/5 6').touch()

    # add and commit
    repo = Repo('.')
    repo.git.add('.')
    repo.git.commit(m='populated for tests')

    # return to home
    os.chdir(original_cwd)


def test_rm_flags():
    populate_test_repo('flags')
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


def test_rm_cwd():
    populate_test_repo('cwd')
    os.chdir('cwd')

    # file
    ret = subprocess.run(['onyo', 'rm', '--yes', 'a'])
    assert ret.returncode == 0
    assert not Path('a').is_file()

    # directory
    ret = subprocess.run(['onyo', 'rm', '--yes', 'simple'])
    assert ret.returncode == 0
    assert not Path('simple').is_dir()


def test_rm_cwd_multiple():
    populate_test_repo('cwd_multiple')
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


def test_rm_nested():
    populate_test_repo('nested')
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


def test_rm_spaces():
    populate_test_repo('spaces')
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


def test_rm_same_target():
    populate_test_repo('same_target')
    os.chdir('same_target')

    # files
    ret = subprocess.run(['onyo', 'rm', '--yes', 'a', 'a', 'a'])
    assert ret.returncode == 0
    assert not Path('a').is_file()

    # directories
    ret = subprocess.run(['onyo', 'rm', '--yes', 'simple', 'simple'])
    assert ret.returncode == 0
    assert not Path('simple').is_dir()


def test_rm_overlap():
    populate_test_repo('overlap')
    os.chdir('overlap')

    ret = subprocess.run(['onyo', 'rm', '--yes', 'overlap/one', 'overlap', 'overlap/two'])
    assert ret.returncode == 0
    assert not Path('overlap').is_dir()


def test_rm_protected():
    populate_test_repo('protected')
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
