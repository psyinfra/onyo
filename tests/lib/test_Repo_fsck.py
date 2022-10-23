import logging
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.lib import OnyoInvalidRepoError
import pytest


#
# Generic
#
variants = [
    'anchors',
    'asset-unique',
    'asset-yaml',
    'clean-tree',
]
@pytest.mark.parametrize('variant', variants)
def test_fsck_empty(caplog, repo, variant):
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    repo.fsck([variant])

    # check log
    # TODO: assert variant in caplog.text


variants = [
    'anchors',
    'asset-unique',
    'asset-yaml',
    'clean-tree',
]
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8')
@pytest.mark.parametrize('variant', variants)
def test_fsck_populated(caplog, repo, variant):
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    repo.fsck([variant])

    # check log
    # TODO: assert variant in caplog.text


variants = [
    '',
    'does-not-exist'
]
@pytest.mark.parametrize('variant', variants)
def test_fsck_invalid_test(caplog, repo, variant):
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    with pytest.raises(ValueError):
        repo.fsck([variant])

    # check log
    # TODO: assert variant in caplog.text


def test_fsck_all(caplog, repo):
    """
    Default is to run all tests.
    """
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    repo.fsck()

    # check log
    # TODO: assert 'anchors' in caplog.text
    # TODO: assert 'asset-unique' in caplog.text
    # TODO: assert 'asset-validate' in caplog.text
    # TODO: assert 'asset-yaml' in caplog.text
    # TODO: assert 'clean-tree' in caplog.text


#
# Anchors
#
@pytest.mark.repo_dirs('r/e/c/u/r/s/i/v/e')
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_anchors_missing(caplog, repo):
    caplog.set_level(logging.INFO, logger='onyo')
    anchors_to_remove = ['a/.anchor', 'r/e/c/.anchor', 'r/e/c/u/r/s/i/v/.anchor']

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


#
# Asset-Unique
#
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'r/e/c/f_5', 'r/e/c/u/r/f_6', 'r/e/c/u/r/s/i/v/e/f_7')
def test_fsck_unique_assets_conflict(caplog, repo):
    caplog.set_level(logging.INFO, logger='onyo')
    assets_to_conflict = ['b/f_1', 'r/e/c/f_3', 'r/e/c/u/r/s/i/v/e/f_5']

    # conflict some asset names
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


#
# Asset-YAML
#
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'r/e/c/f_5', 'r/e/c/u/r/f_6', 'r/e/c/u/r/s/i/v/e/f_7')
def test_fsck_yaml_invalid(caplog, repo):
    caplog.set_level(logging.INFO, logger='onyo')
    files_to_mangle = ['a/f_1', 'r/e/c/f_5', 'r/e/c/u/r/s/i/v/e/f_7']

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


#
# Clean-Tree
#
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_clean_tree_changed(caplog, repo):
    caplog.set_level(logging.INFO, logger='onyo')
    files_to_change = ['a/f_1', 'b/f_3']

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


@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_clean_tree_staged(caplog, repo):
    caplog.set_level(logging.INFO, logger='onyo')
    files_to_stage = ['a/f_1', 'b/f_3']

    # change and stage files
    for i in files_to_stage:
        Path(i).write_text('New contents')

    repo.add(files_to_stage)

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['clean-tree'])

    # check log
    # TODO: assert 'clean-tree' in caplog.text
    for i in files_to_stage:
        assert i in caplog.text


@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5', 'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_clean_tree_untracked(caplog, repo):
    caplog.set_level(logging.INFO, logger='onyo')
    files_to_be_untracked = ['LICENSE', 'd/f_9']

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
