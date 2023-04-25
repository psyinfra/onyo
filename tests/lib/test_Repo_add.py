from pathlib import Path
from typing import Collection, Dict, Iterable, List, Union

import pytest
from onyo import Repo
from tests.conftest import params


@params({
    'str': {"variant": 'single-file'},
    'Path': {"variant": Path('single-file')},
    'list-str': {"variant": ['single-file']},
    'list-Path': {"variant": [Path('single-file')]},
    'set-str': {"variant": {'single-file'}},
    'set-Path': {"variant": {Path('single-file')}},
})
def test_add_args_single_file(
        repo: Repo,
        variant: Union[Iterable[Union[Path, str]], Path, str]) -> None:
    """
    Test `Repo.add()` for a single file with different types.
    """
    Path('single-file').touch()

    # test
    repo.add(variant)
    assert Path(repo.root / 'single-file') in repo.files_staged


@params({
    'list-str': {"variant": ['one', 'two', 'three']},
    'list-Path': {"variant": [Path('one'), Path('two'), Path('three')]},
    'list-mixed': {"variant": ['one', Path('two'), 'three']},
    'set-str': {"variant": {'one', 'two', 'three'}},
    'set-Path': {"variant": {Path('one'), Path('two'), Path('three')}},
    'set-mixed': {"variant": {Path('one'), 'two', Path('three')}},
})
def test_add_args_multi_file(
        repo: Repo,
        variant: Union[Iterable[Union[Path, str]], Path, str]) -> None:
    """
    Test `Repo.add()` for multiple files with different types.
    """
    Path('one').touch()
    Path('two').touch()
    Path('three').touch()

    # test
    repo.add(variant)
    assert Path(repo.root / 'one') in repo.files_staged
    assert Path(repo.root / 'two') in repo.files_staged
    assert Path(repo.root / 'three') in repo.files_staged


@pytest.mark.repo_dirs('single-dir')
@params({
    'str': {"variant": 'single-dir'},
    'Path': {"variant": Path('single-dir')},
    'list-str': {"variant": ['single-dir']},
    'list-Path': {"variant": [Path('single-dir')]},
    'set-str': {"variant": {'single-dir'}},
    'set-Path': {"variant": {Path('single-dir')}},
})
def test_add_args_single_dir(
        repo: Repo,
        variant: Union[Iterable[Union[Path, str]], Path, str]) -> None:
    """
    Test `Repo.add()` for a single directory containing files with different
    types.
    """
    Path('single-dir/file').touch()

    # test
    repo.add(variant)
    assert Path(repo.root / 'single-dir/file') in repo.files_staged


@pytest.mark.repo_dirs('one', 'two', 'three')
@params({
    'list-str': {"variant": ['one', 'two', 'three']},
    'list-Path': {"variant": [Path('one'), Path('two'), Path('three')]},
    'list-mixed': {"variant": ['one', Path('two'), 'three']},
    'set-str': {"variant": {'one', 'two', 'three'}},
    'set-Path': {"variant": {Path('one'), Path('two'), Path('three')}},
    'set-mixed': {"variant": {Path('one'), 'two', Path('three')}},
})
def test_add_args_multi_dir(
        repo: Repo, variant: Collection[Union[Path, str]]) -> None:
    """
    Test `Repo.add()` for multiple directories containing multiple files with
    different types.
    """
    Path('one/file-one-A').touch()
    Path('one/file-one-B').touch()
    Path('two/file-two-A').touch()
    Path('two/file-two-B').touch()
    Path('three/file-three-A').touch()
    Path('three/file-three-B').touch()

    # test
    repo.add(variant)
    for i in variant:
        assert Path(repo.root / f'{i}/file-{i}-A') in repo.files_staged
        assert Path(repo.root / f'{i}/file-{i}-B') in repo.files_staged

    assert len(variant) * 2 == len(repo.files_staged)


@pytest.mark.repo_dirs('r/e/c/u/r/s/i/v/e')
@params({
    'top': {"variant": {'dirs': 'r', 'num': 4}},
    'deep': {"variant": {'dirs': 'r/e/c/u/r/s/i/v/e', 'num': 2}},
    'overlap-same': {"variant": {'dirs': ['r/e/c/u/r', 'r/e/c/u/r/s/i/v/e'],
                                 'num': 2}},
    'overlap-more': {"variant": {'dirs': ['r/e', 'r/e/c/u/r/s/i/v/e'],
                                 'num': 4}},
})
def test_add_dir_recursive(repo: Repo, variant: Dict) -> None:
    """
    Test `Repo.add()` for recursive directories.
    """
    Path('r/e/c/child-r-A').touch()
    Path('r/e/c/child-r-B').touch()
    Path('r/e/c/u/r/s/i/v/e/child-r-A').touch()
    Path('r/e/c/u/r/s/i/v/e/child-r-B').touch()

    # test
    repo.add(variant['dirs'])
    assert variant['num'] == len(repo.files_staged)


@pytest.mark.repo_dirs('d i r')
@params({
    'single': {"variant": ['o n e']},
    'multi': {"variant": ['o n e', 't w o', 'd i r/t h r e e']},
})
def test_add_spaces(repo: Repo, variant: Collection[Union[Path, str]]) -> None:
    """
    Test `Repo.add()` for directories with spaces in their name.
    """
    Path('o n e').touch()
    Path('t w o').touch()
    Path('d i r/t h r e e').touch()

    # test
    repo.add(variant)
    for i in variant:
        assert Path(repo.root / i) in repo.files_staged
    assert len(variant) == len(repo.files_staged)


def test_add_repeat(repo: Repo) -> None:
    """
    Test that `Repo.add()` allows repeated adding of paths without failing.
    """
    Path('repeat-one').touch()
    Path('two').touch()
    Path('three').touch()

    # test
    repo.add(['repeat-one', 'two', 'repeat-one', 'three'])
    assert Path(repo.root / 'repeat-one') in repo.files_staged
    assert Path(repo.root / 'two') in repo.files_staged
    assert Path(repo.root / 'three') in repo.files_staged


@pytest.mark.repo_dirs('unchanged-dir')
@pytest.mark.repo_files('unchanged-file')
@params({
    'file': {"variant": 'unchanged-file'},
    'dir': {"variant": 'unchanged-dir'},
    'mixed': {"variant": ['unchanged-file', 'unchanged-dir']},
})
def test_add_unchanged(repo: Repo, variant: Union[str, List[str]]) -> None:
    """
    Test that `Repo.add()` does not fail on unchanged targets and
    repo.files_staged does not wrongly contain those targets.
    """
    repo.add(variant)
    assert not repo.files_staged


@pytest.mark.repo_dirs('dir')
@params({
    'root': {"variant": ['one', 'not-exist', 'dir/three']},
    'subdir': {"variant": ['one', 'two', 'dir/not-exist']},
})
def test_add_not_exist(repo: Repo, variant: List[str]) -> None:
    """
    Test that `Repo.add()` raises the correct exception on targets that don't
    exist.
    """
    Path('one').touch()
    Path('two').touch()
    Path('dir/three').touch()

    # test
    with pytest.raises(FileNotFoundError):
        repo.add(variant)
    assert not repo.files_staged
