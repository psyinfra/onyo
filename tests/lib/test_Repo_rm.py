from pathlib import Path

import pytest
from onyo.lib import OnyoProtectedPathError


variants = {
    'str': 'single-file',
    'Path': Path('single-file'),
    'list-str': ['single-file'],
    'list-Path': [Path('single-file')],
    'set-str': {'single-file'},
    'set-Path': {Path('single-file')},
}
@pytest.mark.repo_files('single-file', 'untouched')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rm_args_single_file(repo, variant):
    """
    Single file across types.
    """
    repo.rm(variant)
    assert not Path('single-file').exists()
    assert Path('untouched').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = {
    'str': 'single-dir',
    'Path': Path('single-dir'),
    'list-str': ['single-dir'],
    'list-Path': [Path('single-dir')],
    'set-str': {'single-dir'},
    'set-Path': {Path('single-dir')},
}
@pytest.mark.repo_dirs('single-dir', 'untouched')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rm_args_single_dir(repo, variant):
    """
    Single directory across types.
    """
    repo.rm(variant)
    assert not Path('single-dir').exists()
    assert Path('untouched').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = {  # pyre-ignore[9]
    'list-str': ['one', 'two', 'three'],
    'list-Path': [Path('one'), Path('two'), Path('three')],
    'list-mixed': ['one', Path('two'), 'three'],
    'set-str': {'one', 'two', 'three'},
    'set-Path': {Path('one'), Path('two'), Path('three')},
    'set-mixed': {Path('one'), 'two', Path('three')},
}
@pytest.mark.repo_files('one', 'two', 'three', 'untouched')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rm_args_multi_file(repo, variant):
    """
    Multiple files across types.
    """
    repo.rm(variant)
    assert not Path('one').exists()
    assert not Path('two').exists()
    assert not Path('three').exists()
    assert Path('untouched').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = {  # pyre-ignore[9]
    'list-str': ['one', 'two', 'three'],
    'list-Path': [Path('one'), Path('two'), Path('three')],
    'list-mixed': ['one', Path('two'), 'three'],
    'set-str': {'one', 'two', 'three'},
    'set-Path': {Path('one'), Path('two'), Path('three')},
    'set-mixed': {Path('one'), 'two', Path('three')},
}
@pytest.mark.repo_dirs('one', 'two', 'three', 'untouched')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rm_args_multi_dir(repo, variant):
    """
    Multiple directories across types.
    """
    repo.rm(variant)
    assert not Path('one').exists()
    assert not Path('two').exists()
    assert not Path('three').exists()
    assert Path('untouched').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = [  # pyre-ignore[9]
    'not-exist',
    'subdir/not-exist'
]
@pytest.mark.repo_dirs('subdir')
@pytest.mark.parametrize('variant', variants)
def test_rm_not_exist(repo, variant):
    """
    Targets must exist.
    """
    with pytest.raises(FileNotFoundError):
        repo.rm(variant)

    assert Path('subdir').exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = [  # pyre-ignore[9]
    'not-exist',
    'subdir/not-exist'
]
@pytest.mark.repo_dirs('one', 'two', 'subdir')
@pytest.mark.parametrize('variant', variants)
def test_rm_not_exist_mixed(repo, variant):
    """
    All targets must exist.
    """
    with pytest.raises(FileNotFoundError):
        repo.rm(['one', variant, 'two'])

    assert Path('one').exists()
    assert Path('two').exists()
    assert Path('subdir').exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = [  # pyre-ignore[9]
    '.onyo',
    '.git',
    '.onyo/templates',
    '.git/config',
    'one/.anchor',
]
@pytest.mark.repo_dirs('one', 'untouched')
@pytest.mark.parametrize('variant', variants)
def test_rm_protected(repo, variant):
    """
    Protected paths.
    """
    with pytest.raises(OnyoProtectedPathError):
        repo.rm(variant)

    assert Path(variant).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


variants = [  # pyre-ignore[9]
    '.onyo',
    '.git',
    '.onyo/templates',
    '.git/config',
    'dir/.anchor',
]
@pytest.mark.repo_dirs('valid-one', 'valid-two', 'dir')
@pytest.mark.parametrize('variant', variants)
def test_rm_protected_mixed(repo, variant):
    """
    Protected paths.
    """
    with pytest.raises(OnyoProtectedPathError):
        repo.rm(['valid-one', variant, 'valid-two'])

    assert Path('valid-one').exists()
    assert Path('valid-two').exists()
    assert Path(variant).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_dirs('repeat-dir', 'dir-two', 'dir-three')
@pytest.mark.repo_files('repeat-file', 'file-two', 'file-three')
def test_rm_repeat(repo):
    """
    Repeated target paths are OK.
    """
    # files
    repo.rm(['repeat-file', 'file-two', 'repeat-file', 'file-three'])
    assert not Path('repeat-file').exists()
    assert not Path('file-two').exists()
    assert not Path('file-three').exists()

    # directories
    repo.rm(['repeat-dir', 'dir-two', 'dir-three', 'repeat-dir'])
    assert not Path('repeat-dir').exists()
    assert not Path('dir-two').exists()
    assert not Path('dir-three').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_files('overlap/one', 'overlap/two', 'overlap/three')
def test_rm_overlap(repo):
    """
    Overlapping targets.
    """
    repo.rm(['overlap/one', 'overlap', 'overlap/three'])
    assert not Path('overlap').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_files('s p a/c e s/1 2', 's p a/c e s/3 4')
def test_rm_spaces(repo):
    """
    Spaces.
    """
    repo.rm(['s p a/c e s/1 2', 's p a/c e s/3 4'])
    assert not Path('s p a/c e s/1 2').exists()
    assert not Path('s p a/c e s/3 4').exists()
    assert Path('s p a/c e s/').exists()

    repo.rm(['s p a/c e s/'])
    assert not Path('s p a/c e s/').exists()
    assert Path('s p a/').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_dirs('r/e/c/u/r/s/i/v/e')
@pytest.mark.repo_files('one/a', 'two/b')
def test_rm_subdirs(repo):
    """
    Deleting directory contents should leave parent dir intact.
    """
    # files
    repo.rm(['one/a', 'two/b'])
    assert not Path('one/a').is_file()
    assert not Path('two/b').is_file()
    assert Path('one').is_dir()
    assert Path('two').is_dir()

    # directories
    repo.rm('r/e/c/u/r')
    assert not Path('r/e/c/u/r').is_dir()
    assert Path('r/e/c/u').is_dir()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_dirs('r/e/c/u/r/s/i/v/e')
@pytest.mark.repo_files('one/a', 'two/b')
def test_rm_dryrun(repo):
    """
    Dry run should not delete anything.
    """
    repo.rm(['one/a', 'two/b', 'r'], dryrun=True)
    assert Path('one/a').is_file()
    assert Path('two/b').is_file()
    assert Path('r').is_dir()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])


@pytest.mark.repo_dirs('dir/subdir')
@pytest.mark.repo_files('one', 'two')
def test_rm_return_value(repo):
    """
    Return list should contain all items/
    """
    ret = repo.rm(['one', 'two', 'dir'], dryrun=True)
    assert ret
    assert isinstance(ret, list)

    # 2 files + 2 anchors
    assert 4 == len(ret)
    assert 'one' in ret
    assert 'two' in ret
    assert 'dir/.anchor' in ret
    assert 'dir/subdir/.anchor' in ret

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check anchors
    repo.fsck(['anchors'])
