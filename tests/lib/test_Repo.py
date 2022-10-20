import os
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import Repo, OnyoInvalidRepoError
import pytest


def populate_test_repo(path: str, dirs: list = [], files: list = []) -> None:
    # setup repo
    ret = subprocess.run(['onyo', 'init', path])
    assert ret.returncode == 0

    # enter repo
    original_cwd = Path.cwd()
    os.chdir(path)

    # dirs
    ret = subprocess.run(['onyo', 'mkdir'] + dirs)
    assert ret.returncode == 0

    # files
    for i in files:
        Path(i).touch()

    ret = subprocess.run(['git', 'add'] + files)
    assert ret.returncode == 0
    ret = subprocess.run(['git', 'commit', '-m', 'populated for tests'])
    assert ret.returncode == 0

    # return to home
    os.chdir(original_cwd)


#
# instantiation
#
def test_Repo_instantiate_invalid_path():
    with pytest.raises(FileNotFoundError):
        Repo('does-not-exist')


def test_Repo_instantiate_empty_dir():
    Path('empty-dir').mkdir()
    with pytest.raises(OnyoInvalidRepoError):
        Repo('empty-dir')


def test_Repo_instantiate_git_no_onyo():
    ret = subprocess.run(['git', 'init', 'git-no-onyo'])
    assert ret.returncode == 0

    with pytest.raises(OnyoInvalidRepoError):
        Repo('git-no-onyo')


def test_Repo_instantiate_onyo_no_git():
    Path('onyo-no-git/.onyo').mkdir(parents=True)

    with pytest.raises(OnyoInvalidRepoError):
        Repo('onyo-no-git')


def test_Repo_instantiate_string():
    ret = subprocess.run(['onyo', 'init', 'string'])
    assert ret.returncode == 0

    Repo('string')


def test_Repo_instantiate_path():
    ret = subprocess.run(['onyo', 'init', 'path'])
    assert ret.returncode == 0

    Repo(Path('path'))


#
# Repo.assets
#
def test_Repo_assets():
    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('assets', dirs, files)
    os.chdir('assets')
    repo = Repo('.')

    # test
    assert repo.assets
    assert isinstance(repo.assets, set)

    # fewer assets than files
    assert len(repo.assets) < len(repo.files)

    for i in repo.assets:
        assert isinstance(i, Path)
        assert i.is_file()
        # nothing from .git
        assert '.git' not in i.parts
        # nothing from .onyo
        assert '.onyo' not in i.parts
        # no anchors
        assert '.anchor' != i.name
        # TODO: make sure name pattern is for an asset (e.g. not README)

    # make sure all created files are returned
    for i in files:
        # TODO: only check assets
        assert [x for x in repo.files if x.samefile(Path(i))]


#
# Repo.dirs
#
def test_Repo_dirs():
    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('dirs', dirs, files)
    os.chdir('dirs')
    repo = Repo('.')

    # test
    assert repo.dirs
    assert isinstance(repo.dirs, set)

    for i in repo.dirs:
        assert isinstance(i, Path)
        assert i.is_dir()
        # nothing from .git
        assert '.git' not in i.parts

    # make sure all created dirs are returned
    for i in dirs:
        assert [x for x in repo.dirs if x.samefile(Path(i))]

    # should include .onyo
    assert [x for x in repo.dirs if '.onyo' in x.parts]


#
# Repo.files
#
def test_Repo_files():
    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('files', dirs, files)
    os.chdir('files')
    repo = Repo('.')

    # test
    assert repo.files
    assert isinstance(repo.files, set)

    for i in repo.files:
        assert isinstance(i, Path)
        assert i.is_file()
        # nothing from .git
        assert '.git' not in i.parts

    # make sure all created files are returned
    for i in files:
        assert [x for x in repo.files if x.samefile(Path(i))]

    # should include .onyo
    assert [x for x in repo.files if '.onyo' in x.parts]
    # should include .anchors
    assert [x for x in repo.files if '.anchor' == x.name]


#
# Repo.files_changed
#
def test_Repo_files_changed():
    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    files_to_change = ['a/1', 'b/3']

    # setup repo
    populate_test_repo('changed', dirs, files)
    os.chdir('changed')
    repo = Repo('.')

    # change files
    for i in files_to_change:
        Path(i).write_text('New contents')

    # test
    assert repo.files_changed
    assert isinstance(repo.files_changed, set)
    assert len(files_to_change) == len(repo.files_changed)

    for i in repo.files_changed:
        assert isinstance(i, Path)
        assert i.is_file()

    # make sure all changed files are returned
    for i in files_to_change:
        assert [x for x in repo.files_changed if x.samefile(Path(i))]


#
# Repo.files_staged
#
def test_Repo_files_staged():
    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    files_to_stage = ['a/1', 'b/3']

    # setup repo
    populate_test_repo('staged', dirs, files)
    os.chdir('staged')
    repo = Repo('.')

    # change and stage files
    for i in files_to_stage:
        Path(i).write_text('New contents')

    ret = subprocess.run(['git', 'add'] + files_to_stage)
    assert ret.returncode == 0

    # test
    assert repo.files_staged
    assert isinstance(repo.files_staged, set)
    assert len(files_to_stage) == len(repo.files_staged)

    for i in repo.files_staged:
        assert isinstance(i, Path)
        assert i.is_file()

    # make sure all staged files are returned
    for i in files_to_stage:
        assert [x for x in repo.files_staged if x.samefile(Path(i))]


#
# Repo.files_untracked
#
def test_Repo_files_untracked():
    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    files_to_be_untracked = ['LICENSE', 'd/9']

    # setup repo
    populate_test_repo('untracked', dirs, files)
    os.chdir('untracked')
    repo = Repo('.')

    # create untracked files
    for i in files_to_be_untracked:
        Path(i).touch()

    # test
    assert repo.files_untracked
    assert isinstance(repo.files_untracked, set)
    assert len(files_to_be_untracked) == len(repo.files_untracked)

    for i in repo.files_untracked:
        assert isinstance(i, Path)
        assert i.is_file()

    # make sure all untracked files are returned
    for i in files_to_be_untracked:
        assert [x for x in repo.files_untracked if x.samefile(Path(i))]


#
# Repo.opdir
#
def test_Repo_opdir():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-repo'])
    assert ret.returncode == 0

    repo = Repo('opdir-repo')
    assert isinstance(repo.opdir, Path)


def test_Repo_opdir_parent():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-parent'])
    assert ret.returncode == 0

    repo = Repo('opdir-parent')
    assert Path('opdir-parent').samefile(repo.opdir)


def test_Repo_opdir_root():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-root'])
    assert ret.returncode == 0

    os.chdir('opdir-root')
    repo = Repo('.')
    assert Path('.').samefile(repo.opdir)
    assert repo.root.samefile(repo.opdir)


def test_Repo_opdir_child():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-child'])
    assert ret.returncode == 0
    os.chdir('opdir-child')
    ret = subprocess.run(['onyo', 'mkdir', '1/2/3/4/5/6'])
    assert ret.returncode == 0

    os.chdir('1/2/3/4/5/6')
    repo = Repo('.')
    assert Path('.').samefile(repo.opdir)


#
# Repo.root
#
def test_Repo_root():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-repo'])
    assert ret.returncode == 0

    repo = Repo('root-repo')
    assert isinstance(repo.root, Path)


def test_Repo_root_parent():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-parent'])
    assert ret.returncode == 0

    repo = Repo('root-parent')
    assert Path('root-parent').samefile(repo.root)


def test_Repo_root_root():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-root'])
    assert ret.returncode == 0

    os.chdir('root-root')
    repo = Repo('.')
    assert Path('.').samefile(repo.root)


def test_Repo_root_child():
    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-child'])
    assert ret.returncode == 0
    os.chdir('root-child')
    ret = subprocess.run(['onyo', 'mkdir', '1/2/3/4/5/6'])
    assert ret.returncode == 0

    os.chdir('1/2/3/4/5/6')
    repo = Repo('.')
    assert Path('../../../../../../').samefile(repo.root)
