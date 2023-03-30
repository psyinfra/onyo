import subprocess
from pathlib import Path
from typing import Dict, List, Union

import pytest
from onyo import Repo


def last_commit_message() -> str:
    ret = subprocess.run(['git', 'log', '-1', '--pretty=format:%B'],
                         capture_output=True, text=True)
    return ret.stdout


@pytest.mark.parametrize('variant', {'normal title', 525600})
def test_commit_title(repo: Repo, variant: Union[str, int]) -> None:
    """
    Test that `Repo.commit(<msg>)` works for commit messages of different types.
    """
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit(variant)
    msg = last_commit_message()
    assert f'{variant}\n' == msg

@pytest.mark.parametrize('variant', [
    {'args': ('title', 'a two line\ndescription'),
     'output': 'title\n\n' + 'a two line\ndescription'},
    {'args': ('title', 525600),
     'output': 'title\n\n' + '525600'},
    {'args': ('title', Path('file')),
     'output': 'title\n\n' + 'file'},
    {'args': ('title', Path('file').resolve()),
     'output': 'title\n\n' + str(Path('file').resolve())},
    {'args': ('title', 'paragraph one', 'paragraph two'),
     'output': 'title\n\n' + 'paragraph one\n\n' + 'paragraph two'},
])
def test_commit_title_and_description(repo: Repo, variant: Dict) -> None:
    """
    Test that `Repo.commit(<msg>)` works with different arguments of
    different types.
    """
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit(*variant['args'])
    msg = last_commit_message()
    assert f"{variant['output']}\n" == msg


@pytest.mark.parametrize('variant', [['one', 'two', 'three'],
                                     [Path('one'), Path('two'), Path('three')]])
def test_commit_list(repo: Repo, variant: List[Union[str, Path]]) -> None:
    """
    Test that `Repo.commit()` excepts a list as input type.
    """
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit('title', 'List of things:', variant)
    msg = last_commit_message()
    assert 'title\n\n' + 'List of things:\n\n' + 'one\ntwo\nthree\n' == msg


@pytest.mark.parametrize('variant', [{'one', 'two', 'three'},
                                     {Path('one'), Path('two'), Path('three')}])
def test_commit_set(repo: Repo, variant: Dict[str, Path]) -> None:
    """
    Test that `Repo.commit()` excepts a set as input type.
    """
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit('title', 'List of things:', variant)
    msg = last_commit_message()
    assert 'one\n' in msg
    assert 'two\n' in msg
    assert 'three\n' in msg


def test_commit_nothing_staged(repo: Repo) -> None:
    """
    Test that `Repo.commit()` raises the correct error when called while no
    files are staged to commit.
    """
    with pytest.raises(subprocess.CalledProcessError):
        repo.commit('We believe in nothing, Lebowski!')

    msg = last_commit_message()
    assert 'We believe in nothing, Lebowski!' not in msg


@pytest.mark.parametrize('variant', [
    (), '', [], set(), ('title', None), ('title', ''), ('title', []),
    ('title', set())])
def test_commit_empty_message(repo: Repo, variant) -> None:
    """
    Test `Repo.commit()` raises the correct error when called with different
    data types that would result in an empty commit message.
    """
    Path('valid').touch()
    repo.add('valid')
    repo.commit('valid commit')

    Path('file').touch()
    repo.add('file')

    # test
    with pytest.raises(ValueError):
        repo.commit(*variant)

    msg = last_commit_message()
    assert 'valid commit\n' == msg
