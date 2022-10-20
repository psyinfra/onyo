import logging
import os
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import Repo, OnyoInvalidRepoError
import pytest


def test_fsck_anchors_empty(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    helpers.populate_repo('fsck-anchors-empty')
    os.chdir('fsck-anchors-empty')
    repo = Repo('.')

    # test
    repo.fsck(['anchors'])

    # check log
    # TODO: assert 'anchors' in caplog.text


def test_fsck_anchors_populated(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']

    # setup repo
    helpers.populate_repo('fsck-anchors-populated', dirs, files)
    os.chdir('fsck-anchors-populated')
    repo = Repo('.')

    # test
    repo.fsck(['anchors'])

    # check log
    # TODO: assert 'anchors' in caplog.text


def test_fsck_anchors_missing(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd', 'r/e/c/u/r/s/i/v/e']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']
    anchors_to_remove = ['a/.anchor', 'r/e/c/.anchor', 'r/e/c/u/r/s/i/v/.anchor']

    # setup repo
    helpers.populate_repo('fsck-anchors-missing', dirs, files)
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


def test_fsck_unique_assets_empty(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    helpers.populate_repo('fsck-unique-assets-empty')
    os.chdir('fsck-unique-assets-empty')
    repo = Repo('.')

    # test
    repo.fsck(['asset-unique'])

    # check log
    # TODO: assert 'asset-unique' in caplog.text


def test_fsck_unique_assets_populated(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']

    # setup repo
    helpers.populate_repo('fsck-unique-assets-populated', dirs, files)
    os.chdir('fsck-unique-assets-populated')
    repo = Repo('.')

    # test
    repo.fsck(['asset-unique'])

    # check log
    # TODO: assert 'asset-unique' in caplog.text


def test_fsck_unique_assets_conflict(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd', 'r/e/c/u/r/s/i/v/e']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'r/e/c/f_5', 'r/e/c/u/r/f_6', 'r/e/c/u/r/s/i/v/e/f_7']
    assets_to_conflict = ['b/f_1', 'r/e/c/f_3', 'r/e/c/u/r/s/i/v/e/f_5']

    # setup repo
    helpers.populate_repo('fsck-unique-assets-conflict', dirs, files)
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


def test_fsck_yaml_empty(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    helpers.populate_repo('fsck-yaml-empty')
    os.chdir('fsck-yaml-empty')
    repo = Repo('.')

    # test
    repo.fsck(['asset-yaml'])

    # check log
    # TODO: assert 'asset-yaml' in caplog.text


def test_fsck_yaml_populated(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']

    # setup repo
    helpers.populate_repo('fsck-yaml-populated', dirs, files)
    os.chdir('fsck-yaml-populated')
    repo = Repo('.')

    # test
    repo.fsck(['asset-yaml'])

    # check log
    # TODO: assert 'asset-yaml' in caplog.text


def test_fsck_yaml_invalid(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd', 'r/e/c/u/r/s/i/v/e']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'r/e/c/f_5', 'r/e/c/u/r/f_6', 'r/e/c/u/r/s/i/v/e/f_7']
    files_to_mangle = ['a/f_1', 'r/e/c/f_5', 'r/e/c/u/r/s/i/v/e/f_7']

    # setup repo
    helpers.populate_repo('fsck-yaml-invalid', dirs, files)
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


def test_fsck_clean_tree_empty(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    # setup repo
    helpers.populate_repo('fsck-clean-tree-empty')
    os.chdir('fsck-clean-tree-empty')
    repo = Repo('.')

    # test
    repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text


def test_fsck_clean_tree_populated(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']

    # setup repo
    helpers.populate_repo('fsck-clean-tree-populated', dirs, files)
    os.chdir('fsck-clean-tree-populated')
    repo = Repo('.')

    # test
    repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text


def test_fsck_clean_tree_changed(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']
    files_to_change = ['a/f_1', 'b/f_3']

    # setup repo
    helpers.populate_repo('fsck-clean-tree-changed', dirs, files)
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


def test_fsck_clean_tree_staged(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']
    files_to_stage = ['a/f_1', 'b/f_3']

    # setup repo
    helpers.populate_repo('fsck-clean-tree-staged', dirs, files)
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


def test_fsck_clean_tree_untracked(caplog, helpers):
    caplog.set_level(logging.INFO, logger='onyo')

    dirs = ['a', 'b', 'c', 'd']
    files = ['README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8']
    files_to_be_untracked = ['LICENSE', 'd/f_9']

    # setup repo
    helpers.populate_repo('fsck-clean-tree-untracked', dirs, files)
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
