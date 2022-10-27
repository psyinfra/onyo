import os
import subprocess
from pathlib import Path


def test_mv_flags(helpers):
    dirs = ['one', 'two', 'three']
    files = ['a', 'b', 'c', 'one/d', 'two/e', 'three/f']

    # setup repo
    helpers.populate_repo('flags', dirs, files)
    os.chdir('flags')

    # --quiet (requires --yes)
    ret = subprocess.run(['onyo', 'mv', '--quiet', 'a', 'a.quiet'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not Path('a.quiet').exists()
    assert not ret.stdout
    assert ret.stderr

    # --quiet with --yes success
    ret = subprocess.run(['onyo', 'mv', '--quiet', '--yes', 'b', 'two'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert not ret.stderr
    assert not Path('b').exists()
    assert Path('two/b').is_file()

    # --quiet with --yes failure
    ret = subprocess.run(['onyo', 'mv', '--quiet', '--yes', 'does', 'not', 'exist'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    assert not Path('does').exists()
    assert not Path('not').exists()
    assert not Path('exist').exists()

    # --yes success
    ret = subprocess.run(['onyo', 'mv', '--yes', 'c', 'three/c'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('c').exists()
    assert Path('three/c').is_file()


def test_mv_protected(helpers):
    dirs = ['one', 'two', 'three']
    files = ['a', 'b', 'c', 'one/d', 'two/e', 'three/f']

    # setup repo
    helpers.populate_repo('protected', dirs, files)
    os.chdir('protected')

    # cannot rename a file to .anchor
    ret = subprocess.run(['onyo', 'mv', '--yes', 'one/.anchor', '.anchor'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('one/.anchor').is_file()

    # cannot rename a directory to .anchor
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three', '.anchor'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert not Path('.anchor').is_dir()

    # cannot move file into .onyo
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three/f', '.onyo'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('three/f').is_file()
    assert not Path('.onyo/f').exists()

    # cannot move file out of .onyo
    ret = subprocess.run(['onyo', 'mv', '--yes', '.onyo/config', 'one'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('.onyo/config').is_file()
    assert not Path('one/config').exists()

    # cannot move dir into .onyo
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three', '.onyo'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('three').is_dir()
    assert not Path('.onyo/three').is_dir()

    # cannot move dir out of .onyo
    ret = subprocess.run(['onyo', 'mv', '--yes', '.onyo/validation', 'three'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('.onyo/validation').is_dir()
    assert not Path('three/validation').exists()

    # cannot move file into .git
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three/f', '.git'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('three/f').is_file()
    assert not Path('.git/f').exists()

    # cannot move file out of .git
    ret = subprocess.run(['onyo', 'mv', '--yes', '.git/config', 'one'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('.git/config').is_file()
    assert not Path('one/config').exists()

    # cannot move dir into .git
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three', '.git'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('three').is_dir()
    assert not Path('.git/three').exists()

    # cannot move dir out of .git
    ret = subprocess.run(['onyo', 'mv', '--yes', '.git/refs', 'one'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert Path('.git/refs').is_dir()
    assert not Path('one/refs').exists()


def test_mv_rename_file(helpers):
    dirs = ['one', 'two', 'three']
    files = ['a', 'b', 'c', 'one/d', 'two/e', 'three/f']

    # setup repo
    helpers.populate_repo('rename_file', dirs, files)
    os.chdir('rename_file')

    # cannot rename a file
    ret = subprocess.run(['onyo', 'mv', '--yes', 'a', 'a.rename'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    assert Path('a').exists()
    assert not Path('a.rename').is_file()

    # cannot rename a file
    ret = subprocess.run(['onyo', 'mv', '--yes', 'a', 'one/a.rename'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    assert Path('a').exists()
    assert not Path('one/a.rename').is_file()

    # cannot rename a file onto an existing file
    ret = subprocess.run(['onyo', 'mv', '--yes', 'a', 'b'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'cannot be a file' in ret.stderr
    assert Path('a').exists()
    assert Path('b').exists()

    # allowed: same name is not a rename
    ret = subprocess.run(['onyo', 'mv', '--yes', 'b', 'two/b'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('b').exists()
    assert Path('two/b').is_file()

    # same name missing parent
    ret = subprocess.run(['onyo', 'mv', '--yes', 'c', 'not-exist/c'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    assert Path('c').exists()
    assert not Path('not-exist/c').is_file()


def test_mv_rename_dir(helpers):
    dirs = ['one', 'two', 'three', 'four', 's p a/c e s']
    files = []

    # setup repo
    helpers.populate_repo('rename_dir', dirs, files)
    os.chdir('rename_dir')

    # simple
    ret = subprocess.run(['onyo', 'mv', '--yes', 'one', 'one.newname'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('one').exists()
    assert Path('one.newname').is_dir()

    # rename into subdir
    ret = subprocess.run(['onyo', 'mv', '--yes', 'two', 'four/two-rename'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('two').exists()
    assert Path('four/two-rename').is_dir()

    # same-name into subdir
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three', 'four/three'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('three').exists()
    assert Path('four/three').is_dir()

    # spaces
    ret = subprocess.run(['onyo', 'mv', '--yes', 's p a/c e s', 'nospaces'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('s p a/c e s').exists()
    assert Path('nospaces').is_dir()


def test_mv_move_file(helpers):
    dirs = ['s p a c e s', 's p a/c e s', 'one', 'two', 'three']
    files = ['a', 'b', 'c', 'one/d', 'two/e', 'three/f', 's p a c e s/g',
             's p a c e s/h', 's p a c e s/i', 's p a/c e s/1 2']

    # setup repo
    helpers.populate_repo('move_file', dirs, files)
    os.chdir('move_file')

    # NOTE: file names must be unique (otherwise fsck fails) and cannot be
    # renamed. This is why there is no test for moving onto an existing file.

    # single file
    ret = subprocess.run(['onyo', 'mv', '--yes', 'a', 'one'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('a').exists()
    assert Path('one/a').is_file()

    # multiple files
    ret = subprocess.run(['onyo', 'mv', '--yes', 'b', 'c', 'one'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('b').exists()
    assert not Path('c').exists()
    assert Path('one/b').is_file()
    assert Path('one/c').is_file()

    # many depths with spaces
    ret = subprocess.run(['onyo', 'mv', '--yes', 'one/a', 'one/b', 'one/c', 'one/d', 'two/e', 's p a c e s/g', 's p a/c e s/1 2', 'three'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('one/a').exists()
    assert not Path('one/b').exists()
    assert not Path('one/c').exists()
    assert not Path('one/d').exists()
    assert not Path('two/e').exists()
    assert not Path('s p a c e s/g').exists()
    assert not Path('s p a/c e s/1 2').exists()
    assert Path('three/a').is_file()
    assert Path('three/b').is_file()
    assert Path('three/c').is_file()
    assert Path('three/d').is_file()
    assert Path('three/e').is_file()
    assert Path('three/g').is_file()
    assert Path('three/1 2').is_file()

    # destination must exist
    ret = subprocess.run(['onyo', 'mv', 'three/a', 'three/b', 'not_exist'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'does not exist' in ret.stderr
    assert Path('three/a').is_file()
    assert Path('three/b').is_file()
    assert not Path('not_exist').exists()

    # destination must be a directory
    ret = subprocess.run(['onyo', 'mv', 'three/a', 'three/b', 'three/c'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'cannot be a file' in ret.stderr
    assert Path('three/a').is_file()
    assert Path('three/b').is_file()
    assert Path('three/c').is_file()

    # cannot move onto self
    ret = subprocess.run(['onyo', 'mv', 'three/f', 'three/f'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'cannot be a file' in ret.stderr
    assert Path('three/f').is_file()


def test_mv_move_dir(helpers):
    dirs = ['simple', 's p a c e s', 's p a/c e s', 'one', 'two', 'three', 'conflict', 'three/conflict']
    files = []

    # setup repo
    helpers.populate_repo('move_dir', dirs, files)
    os.chdir('move_dir')

    # single dir
    ret = subprocess.run(['onyo', 'mv', '--yes', 'simple', 'one'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('simple').exists()
    assert Path('one/simple').is_dir()

    # multiple dirs
    ret = subprocess.run(['onyo', 'mv', '--yes', 'one', 'two', 'three'], capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('one').exists()
    assert not Path('two').exists()
    assert Path('three/one').is_dir()
    assert Path('three/two').is_dir()

    # many depths with spaces
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three/one', 'three/two', 's p a/c e s', 's p a c e s'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('three/one').exists()
    assert not Path('three/two').exists()
    assert not Path('s p a/c e s').exists()
    assert Path('s p a c e s/one').is_dir()
    assert Path('s p a c e s/two').is_dir()
    assert Path('s p a c e s/c e s').is_dir()

    # cannot move to conflict
    ret = subprocess.run(['onyo', 'mv', '--yes', 'conflict', 'three'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'destinations exist and would conflict' in ret.stderr
    assert Path('conflict').is_dir()
    assert Path('three/conflict').is_dir()
    assert not Path('three/conflict/conflict').is_dir()

    # cannot conflict to self
    ret = subprocess.run(['onyo', 'mv', '--yes', 'three', './'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert 'destinations exist and would conflict' in ret.stderr
    assert Path('three').is_dir()

    # cannot move into self implicitly
    ret = subprocess.run(['onyo', 'mv', 'three', 'three'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "Cannot move 'three' into itself" in ret.stderr
    assert Path('three').is_dir()
    assert not Path('three/three').exists()

    # cannot move into self explicitly
    ret = subprocess.run(['onyo', 'mv', 'three', 'three/three'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "Cannot move 'three' into itself" in ret.stderr
    assert Path('three').is_dir()
    assert not Path('three/three').exists()

    # cannot move into self explicitly
    ret = subprocess.run(['onyo', 'mv', 'three', 'three/new_name'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "Cannot move 'three' into itself" in ret.stderr
    assert Path('three').is_dir()
    assert not Path('three/new_name').exists()

    # destination dir must exist
    ret = subprocess.run(['onyo', 'mv', 'three', 'not-exist/three'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    assert Path('three').is_dir()
    assert not Path('not-exist').exists()


def test_mv_move_mixed(helpers):
    dirs = ['one', 'two', 's p a/c e s', 's p a c e s']
    files = ['a', 'b', 'one/d', 'two/e', 's p a/c e s/1 2', 's p a c e s/g']

    # setup repo
    helpers.populate_repo('move_mixed', dirs, files)
    os.chdir('move_mixed')

    # many depths with spaces
    ret = subprocess.run(['onyo', 'mv', '--yes', 'a', 'one', 'two', 's p a/c e s', 'b', 's p a c e s'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    assert not Path('a').exists()
    assert not Path('one').exists()
    assert not Path('two').exists()
    assert not Path('s p a/c e s').exists()
    assert not Path('b').exists()
    assert Path('s p a c e s/a').is_file()
    assert Path('s p a c e s/one').is_dir()
    assert Path('s p a c e s/two').is_dir()
    assert Path('s p a c e s/c e s').is_dir()
    assert Path('s p a c e s/b').is_file()
