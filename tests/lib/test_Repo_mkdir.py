from pathlib import Path

import pytest
from _pytest.logging import LogCaptureFixture
from onyo import OnyoProtectedPathError, Repo
from typing import List, Union
from tests.conftest import params


def anchored_dir(directory: str) -> bool:
    """
    Returns True if a directory exists and contains an .anchor file.
    Otherwise it returns False.
    """
    if Path(directory).is_dir() and Path(directory, '.anchor').is_file():
        return True

    return False


@params({
    'str': {'variant': 'one'},
    'Path': {'variant': Path('one')},
    'list-str': {'variant': ['one']},
    'list-Path': {'variant': [Path('one')]},
    'set-str': {'variant': {'one'}},
    'set-Path': {'variant': {Path('one')}},
})
def test_mkdir_single(repo: Repo, variant: Union[str, Path]) -> None:
    """
    Test `Repo.mkdir()` with a single directory across types.
    """
    repo.mkdir(variant)
    assert anchored_dir('one')

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@params({
    'list-str': {'variant': ['one', 'two', 'three']},
    'list-Path': {'variant': [Path('one'), Path('two'), Path('three')]},
    'list-mixed': {'variant': ['one', Path('two'), 'three']},
    'set-str': {'variant': {'one', 'two', 'three'}},
    'set-Path': {'variant': {Path('one'), Path('two'), Path('three')}},
    'set-mixed': {'variant': {Path('one'), 'two', Path('three')}},
})
def test_mkdir_multiple_directories(repo: Repo,
                                    variant: List[Union[str, Path]]) -> None:
    """
    Test `Repo.mkdir()` with multiple directories at once across types.
    """
    repo.mkdir(variant)
    assert anchored_dir('one')
    assert anchored_dir('two')
    assert anchored_dir('three')

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@params({
    'single': {'variant': ['o n e']},
    'multi': {'variant': ['o n e', 't w o', 't h r e e']},
    'subdir': {'variant': ['s p a/c e s']},
})
def test_mkdir_spaces(repo: Repo, variant: List[str]) -> None:
    """
    Test `Repo.mkdir()` with directories with spaces in their name.
    """
    repo.mkdir(variant)
    for i in variant:
        assert anchored_dir(i)

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


def test_mkdir_recursive(repo: Repo) -> None:
    """
    Test `Repo.mkdir()` with recursive directories.
    """
    repo.mkdir('r/e/c/u/r/s/i/v/e')
    assert anchored_dir('r')
    assert anchored_dir('r/e')
    assert anchored_dir('r/e/c')
    assert anchored_dir('r/e/c/u')
    assert anchored_dir('r/e/c/u/r')
    assert anchored_dir('r/e/c/u/r/s')
    assert anchored_dir('r/e/c/u/r/s/i')
    assert anchored_dir('r/e/c/u/r/s/i/v')
    assert anchored_dir('r/e/c/u/r/s/i/v/e')

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@params({
    'implicit': {"variant": ['overlap/one', 'overlap/two', 'overlap/three']},
    'explicit': {"variant": ['overlap', 'overlap/one', 'overlap/two', 'overlap/three']}
})
def test_mkdir_overlap(repo: Repo, variant: List[str]) -> None:
    """
    Test that `Repo.mkdir()` correctly creates and anchors sub-directories when
    some directories already exist.
    """
    repo.mkdir(variant)

    assert anchored_dir('overlap')
    assert anchored_dir('overlap/one')
    assert anchored_dir('overlap/two')
    assert anchored_dir('overlap/three')
    assert not Path('overlap/overlap').exists()
    assert not Path('overlap/one/overlap').exists()
    assert not Path('overlap/two/overlap').exists()
    assert not Path('overlap/three/overlap').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.parametrize('variant', [
    '.onyo/protected',
    '.git/protected',
    'protected/.git',
    'protected/.onyo',
    'one/.anchor',
])
def test_mkdir_protected(repo: Repo, variant: str) -> None:
    """
    Test that `Repo.mkdir()` raises correct errors when called on
    protected paths.
    """
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir(variant)

    assert not Path(variant).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.parametrize('variant', [
    '.onyo/protected',
    '.git/protected',
    'protected/.git',
    'protected/.onyo',
    'one/.anchor',
])
def test_mkdir_protected_mixed(caplog: LogCaptureFixture, repo: Repo,
                               variant: str) -> None:
    """
    Test that `Repo.mkdir()` first checks all paths of a list and errors if some
    are protected paths.
    """
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir(['valid-one', variant, 'valid-two'])

    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert not Path(variant).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'valid-one' not in caplog.text
    assert 'valid-two' not in caplog.text
    assert variant in caplog.text

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_dirs('exists-dir', 'subdir/exists-dir')
@pytest.mark.parametrize('variant', [
    'exists-dir',
    'subdir/exists-dir'
])
def test_mkdir_exists_dir(caplog: LogCaptureFixture, repo: Repo,
                          variant: str) -> None:
    """
    Test that `Repo.mkdir()` cannot re-create an existing directory.
    """
    with pytest.raises(FileExistsError):
        repo.mkdir(variant)

    assert anchored_dir(variant)
    assert not anchored_dir(f'{variant}/{variant}')

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert variant in caplog.text

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_files('exists-file', 'subdir/exists-subfile')
@pytest.mark.parametrize('variant', [
    'exists-file',
    'subdir/exists-subfile'
])
def test_mkdir_exists_file(caplog: LogCaptureFixture, repo: Repo,
                           variant: str) -> None:
    """
    Test that `Repo.mkdir()` does not except a file as target.
    """
    with pytest.raises(FileExistsError):
        repo.mkdir(variant)

    assert Path(variant).is_file()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert variant in caplog.text

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_dirs('exists-dir')
@pytest.mark.repo_files('exists-file')
@pytest.mark.parametrize('variant', [
    'exists-file',
    'exists-dir'
])
def test_mkdir_exists_mixed(caplog: LogCaptureFixture, repo: Repo,
                            variant: str) -> None:
    """
    Test that `Repo.mkdir()` raises the correct error if a target already
    exists.
    """
    with pytest.raises(FileExistsError):
        repo.mkdir(['valid-one', variant, 'valid-two'])

    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert Path('exists-file').exists()
    assert anchored_dir('exists-dir')

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'valid-one' not in caplog.text
    assert 'valid-two' not in caplog.text
    assert variant in caplog.text

    # check anchors
    repo.fsck(['anchors'])
