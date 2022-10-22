import subprocess
from pathlib import Path
import pytest


def last_commit_message() -> str:
    ret = subprocess.run(['git', 'log', '-1', '--pretty=format:%B'],
                         capture_output=True, text=True)
    return ret.stdout


variants = {
    'str': 'normal title',
    'int': 525600,
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_commit_title(repo, variant):
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit(variant)
    msg = last_commit_message()
    assert f'{variant}\n' == msg


variants = {  # pyre-ignore[9]
    'str': {'args': ('title', 'a two line\ndescription'),
            'output': 'title\n\n' + 'a two line\ndescription'},
    'int': {'args': ('title', 525600),
            'output': 'title\n\n' + '525600'},
    'Path-rel': {'args': ('title', Path('file')),
                 'output': 'title\n\n' + 'file'},
    'Path-abs': {'args': ('title', Path('file').resolve()),
                 'output': 'title\n\n' + str(Path('file').resolve())},
    'multiple': {'args': ('title', 'paragraph one', 'paragraph two'),
                 'output': 'title\n\n' + 'paragraph one\n\n' + 'paragraph two'},
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_commit_title_and_description(repo, variant):
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit(*variant['args'])
    msg = last_commit_message()
    assert f"{variant['output']}\n" == msg


variants = {  # pyre-ignore[9]
    'list-str': ['one', 'two', 'three'],
    'list-Path': [Path('one'), Path('two'), Path('three')],
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_commit_list(repo, variant):
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit('title', 'List of things:', variant)
    msg = last_commit_message()
    assert 'title\n\n' + 'List of things:\n\n' + 'one\ntwo\nthree\n' == msg


variants = {  # pyre-ignore[9]
    'set-str': {'one', 'two', 'three'},
    'set-Path': {Path('one'), Path('two'), Path('three')},
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_commit_set(repo, variant):
    Path('file').touch()
    repo.add('file')

    # test
    repo.commit('title', 'List of things:', variant)
    msg = last_commit_message()
    assert 'one\n' in msg
    assert 'two\n' in msg
    assert 'three\n' in msg


def test_commit_nothing(repo):
    with pytest.raises(subprocess.CalledProcessError):
        repo.commit('We believe in nothing Lebowski!')

    msg = last_commit_message()
    assert 'We believe in nothing Lebowski!' not in msg
