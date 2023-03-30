from pathlib import Path
from typing import Collection, Dict, Iterable, List, Union

import pytest
from onyo import Repo


@pytest.mark.parametrize('variant', [
    'single-file', Path('single-file'), ['single-file'], [Path('single-file')],
    {'single-file'}, {Path('single-file')}])
def test_add_args_single_file(
        repo: Repo,
        variant: Union[Iterable[Union[Path, str]], Path, str]) -> None:
    """
    Test `Repo.add()` for a single file with different types.
    """
    Path('single-file').touch()

    # test
    repo.add(variant)
    assert Path('single-file') in repo.files_staged


@pytest.mark.parametrize('variant', [
    ['one', 'two', 'three'], [Path('one'), Path('two'), Path('three')],
    ['one', Path('two'), 'three'], {'one', 'two', 'three'},
    {Path('one'), Path('two'), Path('three')},
    {Path('one'), 'two', Path('three')}])
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
    assert Path('one') in repo.files_staged
    assert Path('two') in repo.files_staged
    assert Path('three') in repo.files_staged


@pytest.mark.repo_dirs('single-dir')
@pytest.mark.parametrize('variant', [
    'single-dir', Path('single-dir'), ['single-dir'], [Path('single-dir')],
    {'single-dir'}, {Path('single-dir')}])
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
    assert Path('single-dir/file') in repo.files_staged


@pytest.mark.repo_dirs('one', 'two', 'three')
@pytest.mark.parametrize('variant', [
    ['one', 'two', 'three'], [Path('one'), Path('two'), Path('three')],
    ['one', Path('two'), 'three'], {'one', 'two', 'three'},
    {Path('one'), Path('two'), Path('three')},
    {Path('one'), 'two', Path('three')}])
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
        assert Path(f'{i}/file-{i}-A') in repo.files_staged
        assert Path(f'{i}/file-{i}-B') in repo.files_staged

    assert len(variant) * 2 == len(repo.files_staged)


@pytest.mark.repo_dirs('r/e/c/u/r/s/i/v/e')
@pytest.mark.parametrize('variant', [
    {'dirs': 'r', 'num': 4}, {'dirs': 'r/e/c/u/r/s/i/v/e', 'num': 2},
    {'dirs': ['r/e/c/u/r', 'r/e/c/u/r/s/i/v/e'], 'num': 2},
    {'dirs': ['r/e', 'r/e/c/u/r/s/i/v/e'], 'num': 4}])
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
@pytest.mark.parametrize('variant', [
    ['o n e'], ['o n e', 't w o', 'd i r/t h r e e']])
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
        assert Path(i) in repo.files_staged
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
    assert Path('repeat-one') in repo.files_staged
    assert Path('two') in repo.files_staged
    assert Path('three') in repo.files_staged


@pytest.mark.repo_dirs('unchanged-dir')
@pytest.mark.repo_files('unchanged-file')
@pytest.mark.parametrize('variant', ['unchanged-file', 'unchanged-dir',
                                     ['unchanged-file', 'unchanged-dir']])
def test_add_unchanged(repo: Repo, variant: Union[str, List[str]]) -> None:
    """
    Test that `Repo.add()` does not fail on unchanged targets and
    repo.files_staged does not wrongly contain those targets.
    """
    repo.add(variant)
    assert not repo.files_staged


@pytest.mark.repo_dirs('dir')
@pytest.mark.parametrize('variant', [
    ['one', 'not-exist', 'dir/three'], ['one', 'two', 'dir/not-exist']])
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
