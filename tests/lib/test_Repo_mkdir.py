from pathlib import Path

import pytest
from onyo.lib import OnyoProtectedPathError


def anchored_dir(directory):
    """
    Returns True if a directory exists and contains an .anchor file.
    Otherwise it returns False.
    """
    if Path(directory).is_dir() and Path(directory, '.anchor').is_file():
        return True

    return False


variants = {
    'str': 'one',
    'Path': Path('one'),
    'list-str': ['one'],
    'list-Path': [Path('one')],
    'set-str': {'one'},
    'set-Path': {Path('one')},
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_mkdir_single(repo, variant):
    """
    Single directory across types.
    """
    repo.mkdir(variant)
    assert anchored_dir('one')

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = {  # pyre-ignore[9]
    'list-str': ['one', 'two', 'three'],
    'list-Path': [Path('one'), Path('two'), Path('three')],
    'list-mixed': ['one', Path('two'), 'three'],
    'set-str': {'one', 'two', 'three'},
    'set-Path': {Path('one'), Path('two'), Path('three')},
    'set-mixed': {Path('one'), 'two', Path('three')},
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_mkdir_multi(repo, variant):
    """
    Multiple directories across types.
    """
    repo.mkdir(variant)
    assert anchored_dir('one')
    assert anchored_dir('two')
    assert anchored_dir('three')

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = {
    'single': ['o n e'],
    'multi': ['o n e', 't w o', 't h r e e'],
    'subdir': ['s p a/c e s'],
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_mkdir_spaces(repo, variant):
    """
    Spaces.
    """
    repo.mkdir(variant)
    for i in variant:
        assert anchored_dir(i)

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


def test_mkdir_recursive(repo):
    """
    Recursive directories.
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

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = {
    'implicit': ['overlap/one', 'overlap/two', 'overlap/three'],
    'explicit': ['overlap', 'overlap/one', 'overlap/two', 'overlap/three']
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_mkdir_overlap(repo, variant):
    repo.mkdir(variant)

    assert anchored_dir('overlap')
    assert anchored_dir('overlap/one')
    assert anchored_dir('overlap/two')
    assert anchored_dir('overlap/three')
    assert not Path('overlap/overlap').exists()
    assert not Path('overlap/one/overlap').exists()
    assert not Path('overlap/two/overlap').exists()
    assert not Path('overlap/three/overlap').exists()

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = [  # pyre-ignore[9]
    '.onyo/protected',
    '.git/protected',
    'protected/.git',
    'protected/.onyo',
    'one/.anchor',
]
@pytest.mark.parametrize('variant', variants)
def test_mkdir_protected(repo, variant):
    """
    Protected paths.
    """
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir(variant)

    assert not Path(variant).exists()

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = [  # pyre-ignore[9]
    '.onyo/protected',
    '.git/protected',
    'protected/.git',
    'protected/.onyo',
    'one/.anchor',
]
@pytest.mark.parametrize('variant', variants)
def test_mkdir_protected_mixed(repo, variant, caplog):
    """
    Protected paths.
    """
    with pytest.raises(OnyoProtectedPathError):
        repo.mkdir(['valid-one', variant, 'valid-two'])

    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert not Path(variant).exists()

    # check log
    assert 'valid-one' not in caplog.text
    assert 'valid-two' not in caplog.text
    assert variant in caplog.text

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = [  # pyre-ignore[9]
    'exists-dir',
    'subdir/exists-dir',
]
@pytest.mark.repo_dirs('exists-dir', 'subdir/exists-dir')
@pytest.mark.parametrize('variant', variants)
def test_mkdir_exists_dir(repo, variant, caplog):
    """
    TODO
    """
    with pytest.raises(FileExistsError):
        repo.mkdir(variant)

    assert anchored_dir(variant)
    assert not anchored_dir(f'{variant}/{variant}')

    # check log
    assert variant in caplog.text

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = [  # pyre-ignore[9]
    'exists-file',
    'subdir/exists-subfile',
]
@pytest.mark.repo_files('exists-file', 'subdir/exists-subfile')
@pytest.mark.parametrize('variant', variants)
def test_mkdir_exists_file(repo, variant, caplog):
    """
    TODO
    """
    with pytest.raises(FileExistsError):
        repo.mkdir(variant)

    assert Path(variant).is_file()

    # check log
    assert variant in caplog.text

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])


variants = [  # pyre-ignore[9]
    'exists-file',
    'exists-dir',
]
@pytest.mark.repo_dirs('exists-dir')
@pytest.mark.repo_files('exists-file')
@pytest.mark.parametrize('variant', variants)
def test_mkdir_exists_mixed(repo, variant, caplog):
    """
    TODO
    """
    with pytest.raises(FileExistsError):
        repo.mkdir(['valid-one', variant, 'valid-two'])

    assert not Path('valid-one').exists()
    assert not Path('valid-two').exists()
    assert Path('exists-file').exists()
    assert anchored_dir('exists-dir')

    # check log
    assert 'valid-one' not in caplog.text
    assert 'valid-two' not in caplog.text
    assert variant in caplog.text

    # make sure everything is clean
    repo.fsck(['anchors', 'clean-tree'])
