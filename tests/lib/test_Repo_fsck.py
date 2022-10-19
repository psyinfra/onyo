import logging
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
    if dirs:
        ret = subprocess.run(['onyo', 'mkdir'] + dirs)
        assert ret.returncode == 0

    # files
    if files:
        for i in files:
            Path(i).touch()

        ret = subprocess.run(['git', 'add'] + files)
        assert ret.returncode == 0
        ret = subprocess.run(['git', 'commit', '-m', 'populated for tests'])
        assert ret.returncode == 0

    # return to home
    os.chdir(original_cwd)


def test_fsck_anchors_empty(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    populate_test_repo('fsck-anchors-empty')
    os.chdir('fsck-anchors-empty')
    repo = Repo('.')

    # test
    repo.fsck(['anchors'])

    # check log
    # TODO: assert 'anchors' in caplog.text


def test_fsck_anchors_populated(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('fsck-anchors-populated', dirs, files)
    os.chdir('fsck-anchors-populated')
    repo = Repo('.')

    # test
    repo.fsck(['anchors'])

    # check log
    # TODO: assert 'anchors' in caplog.text


def test_fsck_anchors_missing(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd', 'r/e/c/u/r/s/i/v/e']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    anchors_to_remove = ['a/.anchor', 'r/e/c/.anchor', 'r/e/c/u/r/s/i/v/.anchor']

    # setup repo
    populate_test_repo('fsck-anchors-missing', dirs, files)
    os.chdir('fsck-anchors-missing')
    repo = Repo('.')

    # remove anchors
    repo._git(['rm'] + anchors_to_remove)
    repo.commit('remove anchors')

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['anchors'])

    # check log
    # TODO: assert 'anchors' in caplog.text
    for i in anchors_to_remove:
        assert i in caplog.text
    assert len(anchors_to_remove) == caplog.text.count('/.anchor')


def test_fsck_unique_assets_empty(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    populate_test_repo('fsck-unique-assets-empty')
    os.chdir('fsck-unique-assets-empty')
    repo = Repo('.')

    # test
    repo.fsck(['asset-unique'])

    # check log
    # TODO: assert 'asset-unique' in caplog.text


def test_fsck_unique_assets_populated(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('fsck-unique-assets-populated', dirs, files)
    os.chdir('fsck-unique-assets-populated')
    repo = Repo('.')

    # test
    repo.fsck(['asset-unique'])

    # check log
    # TODO: assert 'asset-unique' in caplog.text


def test_fsck_unique_assets_conflict(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd', 'r/e/c/u/r/s/i/v/e']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'r/e/c/5', 'r/e/c/u/r/6', 'r/e/c/u/r/s/i/v/e/7']
    assets_to_conflict = ['b/1', 'r/e/c/3', 'r/e/c/u/r/s/i/v/e/5']

    # setup repo
    populate_test_repo('fsck-unique-assets-conflict', dirs, files)
    os.chdir('fsck-unique-assets-conflict')
    repo = Repo('.')

    # mangle files
    for i in assets_to_conflict:
        Path(i).touch()

    repo.add(assets_to_conflict)
    repo.commit('add conflicts')

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['asset-unique'])

    # check log
    # TODO: assert 'asset-unique' in caplog.text
    for i in assets_to_conflict:
        assert i in caplog.text
        assert 2 == caplog.text.count(Path(i).name)


def test_fsck_yaml_empty(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    populate_test_repo('fsck-yaml-empty')
    os.chdir('fsck-yaml-empty')
    repo = Repo('.')

    # test
    repo.fsck(['asset-yaml'])

    # check log
    # TODO: assert 'asset-yaml' in caplog.text


def test_fsck_yaml_populated(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('fsck-yaml-populated', dirs, files)
    os.chdir('fsck-yaml-populated')
    repo = Repo('.')

    # test
    repo.fsck(['asset-yaml'])

    # check log
    # TODO: assert 'asset-yaml' in caplog.text


def test_fsck_yaml_invalid(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd', 'r/e/c/u/r/s/i/v/e']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'r/e/c/5', 'r/e/c/u/r/6', 'r/e/c/u/r/s/i/v/e/7']
    files_to_mangle = ['a/1', 'r/e/c/5', 'r/e/c/u/r/s/i/v/e/7']

    # setup repo
    populate_test_repo('fsck-yaml-invalid', dirs, files)
    os.chdir('fsck-yaml-invalid')
    repo = Repo('.')

    # mangle files
    for i in files_to_mangle:
        Path(i).write_text('dsfs: sdf: sdf:dd ad123e')

    repo.add(files_to_mangle)
    repo.commit('mangle files')

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['asset-yaml'])

    # check log
    # TODO: assert 'asset-yaml' in caplog.text
    for i in files_to_mangle:
        assert i in caplog.text


def test_fsck_clean_tree_empty(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    populate_test_repo('fsck-clean-tree-empty')
    os.chdir('fsck-clean-tree-empty')
    repo = Repo('.')

    # test
    repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text


def test_fsck_clean_tree_populated(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # setup repo
    populate_test_repo('fsck-clean-tree-populated', dirs, files)
    os.chdir('fsck-clean-tree-populated')
    repo = Repo('.')

    # test
    repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text


def test_fsck_clean_tree_changed(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    files_to_change = ['a/1', 'b/3']

    # setup repo
    populate_test_repo('fsck-clean-tree-changed', dirs, files)
    os.chdir('fsck-clean-tree-changed')
    repo = Repo('.')

    # change files
    for i in files_to_change:
        Path(i).write_text('New contents')

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text
    for i in files_to_change:
        assert i in caplog.text


def test_fsck_clean_tree_staged(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    files_to_stage = ['a/1', 'b/3']

    # setup repo
    populate_test_repo('fsck-clean-tree-staged', dirs, files)
    os.chdir('fsck-clean-tree-staged')
    repo = Repo('.')

    # change and stage files
    for i in files_to_stage:
        Path(i).write_text('New contents')

    ret = subprocess.run(['git', 'add'] + files_to_stage)
    assert ret.returncode == 0

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text
    for i in files_to_stage:
        assert i in caplog.text


def test_fsck_clean_tree_untracked(caplog):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']
    files_to_be_untracked = ['LICENSE', 'd/9']

    # setup repo
    populate_test_repo('fsck-clean-tree-untracked', dirs, files)
    os.chdir('fsck-clean-tree-untracked')
    repo = Repo('.')

    # create untracked files
    for i in files_to_be_untracked:
        Path(i).touch()

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text
    for i in files_to_be_untracked:
        assert i in caplog.text
