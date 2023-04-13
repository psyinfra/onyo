import logging
from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
from onyo.lib import Repo, OnyoInvalidRepoError

#
# Generic
#
@pytest.mark.parametrize('variant', ['anchors', 'asset-unique',
                                     'asset-yaml', 'clean-tree'])
def test_fsck_empty(
        caplog: LogCaptureFixture, repo: Repo, variant: str) -> None:
    """
    Run different types of fsck on a clean and empty repository without error.
    """
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    repo.fsck([variant])

    # check log
    # TODO: assert variant in caplog.text


@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5',
                        'c/f_6', 'd/f_7', 'd/f_8')
@pytest.mark.parametrize('variant', ['anchors', 'asset-unique',
                                     'asset-yaml', 'clean-tree'])
def test_fsck_populated(caplog: LogCaptureFixture,
                        repo: Repo, variant: str) -> None:
    """
    Run different types of fsck on an non-empty but clean repository without
    error.
    """
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    repo.fsck([variant])

    # check log
    # TODO: assert variant in caplog.text


@pytest.mark.parametrize('variant', ['', 'does-not-exist'])
def test_fsck_invalid_test(caplog: LogCaptureFixture,
                           repo: Repo, variant: str) -> None:
    """
    Test that when `Repo.fsck()` is called with an non-existing fsck the correct
    error gets raised.
    """
    caplog.set_level(logging.INFO, logger='onyo')

    # test
    with pytest.raises(ValueError):
        repo.fsck([variant])

    # check log
    # TODO: assert variant in caplog.text


def test_fsck_all(caplog: LogCaptureFixture, repo: Repo) -> None:
    """
    Test that `repo.fsck()` runs per default all tests.
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
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5',
                        'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_anchors_missing(caplog: LogCaptureFixture, repo: Repo) -> None:
    """
    Test that `Repo.fsck()` fails when `.anchor` files are missing.
    """
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
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4',
                        'r/e/c/f_5', 'r/e/c/u/r/f_6', 'r/e/c/u/r/s/i/v/e/f_7')
def test_fsck_unique_assets_conflict(caplog: LogCaptureFixture,
                                     repo: Repo) -> None:
    """
    Test that `Repo.fsck()` fails if multiple assets with the same name exist.
    """
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
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4',
                        'r/e/c/f_5', 'r/e/c/u/r/f_6', 'r/e/c/u/r/s/i/v/e/f_7')
@pytest.mark.repo_contents(['a/f_1', 'dsfs: sdf: sdf:dd ad123e'],
                           ['r/e/c/f_5', 'dsfs: sdf: sdf:dd ad123e'],
                           ['r/e/c/u/r/s/i/v/e/f_7',
                            'dsfs: sdf: sdf:dd ad123e'])
def test_fsck_yaml_invalid(caplog: LogCaptureFixture, repo: Repo) -> None:
    """
    Test that `Repo.fsck()` identifies files with invalid YAML syntax inside of
    a populated repository.
    """
    caplog.set_level(logging.INFO, logger='onyo')
    files_to_mangle = ['a/f_1', 'r/e/c/f_5', 'r/e/c/u/r/s/i/v/e/f_7']

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['asset-yaml'])

    # check log
    # TODO: assert 'asset-yaml' in caplog.text
    for i in files_to_mangle:
        assert i in caplog.text


@pytest.mark.parametrize('content', [
    "type: value", "make: value", "model: value", "serial: value",
    "key: value\ntype: value\nfield: value"])
def test_fsck_yaml_contains_pseudo_key(caplog: LogCaptureFixture,
                                       repo: Repo, content: str) -> None:
    """
    Test that the fsck fails when an asset contains a pseudo-key.
    """
    caplog.set_level(logging.INFO, logger='onyo')
    test_asset = "laptop_apple_macbook.0"

    # add an invalid pseudo key to an asset
    Path(test_asset).write_text(content)
    repo.add(test_asset)
    repo.commit('Add asset with pseudo-key')

    # test
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['pseudo-keys'])

    # check log
    assert test_asset in caplog.text
    assert "contain pseudo keys" in caplog.text


@pytest.mark.parametrize('content', [
    "key_one: type", "key_two: make", "key_three: model", "key_four: serial",
    "key_five: 'model: value'", "key_type: key_six", "key_serial: key_seven"])
def test_fsck_yaml_allows_valid_keys(caplog: LogCaptureFixture, repo: Repo,
                                     content: str) -> None:
    """
    Test that the fsck does not fail when an asset contains a key, where a valid
    key where just a part of it is a pseudo-key, and that pseudo-keys as values
    are still allowed.
    """
    caplog.set_level(logging.INFO, logger='onyo')
    test_asset = "laptop_apple_macbook.0"

    # add an invalid pseudo key to an asset
    Path(test_asset).write_text(content)
    repo.add(test_asset)
    repo.commit('Add asset with pseudo-key')

    # test
    repo.fsck(['pseudo-keys'])

    # check log
    assert not caplog.text


#
# Clean-Tree
#
@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5',
                        'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_clean_tree_changed(caplog: LogCaptureFixture, repo: Repo) -> None:
    """
    Test that `Repo.fsck()` fails if the git tree contains changed files.
    """
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


@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5',
                        'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_clean_tree_staged(caplog: LogCaptureFixture, repo: Repo) -> None:
    """
    Test that `Repo.fsck()` fails if the git tree contains staged files.
    """
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


@pytest.mark.repo_files('README', 'a/f_1', 'a/f_2', 'b/f_3', 'b/f_4', 'c/f_5',
                        'c/f_6', 'd/f_7', 'd/f_8')
def test_fsck_clean_tree_untracked(caplog: LogCaptureFixture,
                                   repo: Repo) -> None:
    """
    Test that `Repo.fsck()` fails if the git tree contains untracked files.
    """
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
