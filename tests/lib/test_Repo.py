import os
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import Repo, OnyoInvalidRepoError
import pytest


#
# instantiation
#
variants = {
    'str': 'the-repo',
    'Path': Path('the-repo'),
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_Repo_instantiate_types(tmp_path, variant):
    os.chdir(tmp_path)
    ret = subprocess.run(['onyo', 'init', 'the-repo'])
    assert ret.returncode == 0

    # test
    Repo(variant)


def test_Repo_instantiate_invalid_path(tmp_path):
    repo_path = Path(tmp_path, 'does-not-exist')

    with pytest.raises(FileNotFoundError):
        Repo(repo_path)


def test_Repo_instantiate_empty_dir(tmp_path):
    repo_path = Path(tmp_path)
    with pytest.raises(OnyoInvalidRepoError):
        Repo(repo_path)


def test_Repo_instantiate_git_no_onyo(tmp_path):
    repo_path = Path(tmp_path)
    ret = subprocess.run(['git', 'init', str(repo_path)])
    assert ret.returncode == 0

    # test
    with pytest.raises(OnyoInvalidRepoError):
        Repo(repo_path)


def test_Repo_instantiate_onyo_no_git(tmp_path):
    repo_path = Path(tmp_path)
    Path(repo_path, '.onyo').mkdir()

    with pytest.raises(OnyoInvalidRepoError):
        Repo(repo_path)


#
# Repo.assets
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8')
def test_Repo_assets(repo):
    assets = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

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
    for i in assets:
        # TODO: only check assets
        assert [x for x in repo.files if x.samefile(Path(i))]


#
# Repo.dirs
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8')
def test_Repo_dirs(repo):
    dirs = ['a', 'b', 'c', 'd']

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
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8')
def test_Repo_files(repo):
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

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
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8')
def test_Repo_files_changed(repo):
    files_to_change = ['a/1', 'b/3']
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
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8')
def test_Repo_files_staged(repo):
    files_to_stage = ['a/1', 'b/3']

    # change and stage files
    for i in files_to_stage:
        Path(i).write_text('New contents')

    repo.add(files_to_stage)

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
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8')
def test_Repo_files_untracked(repo):
    files_to_be_untracked = ['LICENSE', 'd/9']

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
def test_Repo_opdir(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-repo'])
    assert ret.returncode == 0

    # test
    repo = Repo('opdir-repo')
    assert isinstance(repo.opdir, Path)


def test_Repo_opdir_parent(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-parent'])
    assert ret.returncode == 0

    # test
    repo = Repo('opdir-parent')
    assert Path('opdir-parent').samefile(repo.opdir)


def test_Repo_opdir_root(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-root'])
    assert ret.returncode == 0

    # test
    os.chdir('opdir-root')
    repo = Repo('.')
    assert Path('.').samefile(repo.opdir)
    assert repo.root.samefile(repo.opdir)


def test_Repo_opdir_child(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-child'])
    assert ret.returncode == 0
    os.chdir('opdir-child')
    ret = subprocess.run(['onyo', 'mkdir', '1/2/3/4/5/6'])
    assert ret.returncode == 0

    # test
    os.chdir('1/2/3/4/5/6')
    repo = Repo('.')
    assert Path('.').samefile(repo.opdir)


#
# Repo.root
#
def test_Repo_root(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-repo'])
    assert ret.returncode == 0

    repo = Repo('root-repo')
    assert isinstance(repo.root, Path)


def test_Repo_root_parent(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-parent'])
    assert ret.returncode == 0

    # test
    repo = Repo('root-parent')
    assert Path('root-parent').samefile(repo.root)


def test_Repo_root_root(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-root'])
    assert ret.returncode == 0

    # test
    os.chdir('root-root')
    repo = Repo('.')
    assert Path('.').samefile(repo.root)


def test_Repo_root_child(tmp_path):
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-child'])
    assert ret.returncode == 0
    os.chdir('root-child')
    ret = subprocess.run(['onyo', 'mkdir', '1/2/3/4/5/6'])
    assert ret.returncode == 0

    # test
    os.chdir('1/2/3/4/5/6')
    repo = Repo('.')
    assert Path('../../../../../../').samefile(repo.root)
