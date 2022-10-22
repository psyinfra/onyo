from pathlib import Path
import pytest


variants = {
    'str': 'single-file',
    'Path': Path('single-file'),
    'list-str': ['single-file'],
    'list-Path': [Path('single-file')],
    'set-str': {'single-file'},
    'set-Path': {Path('single-file')},
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_args_single_file(repo, variant):
    """
    Single file across types.
    """
    Path('single-file').touch()

    # test
    repo.add(variant)
    assert Path('single-file') in repo.files_staged


variants = {  # pyre-ignore[9]
    'list-str': ['one', 'two', 'three'],
    'list-Path': [Path('one'), Path('two'), Path('three')],
    'list-mixed': ['one', Path('two'), 'three'],
    'set-str': {'one', 'two', 'three'},
    'set-Path': {Path('one'), Path('two'), Path('three')},
    'set-mixed': {Path('one'), 'two', Path('three')},
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_args_multi_file(repo, variant):
    """
    Multiple files across types.
    """
    Path('one').touch()
    Path('two').touch()
    Path('three').touch()

    # test
    repo.add(variant)
    assert Path('one') in repo.files_staged
    assert Path('two') in repo.files_staged
    assert Path('three') in repo.files_staged


variants = {
    'str': 'single-dir',
    'Path': Path('single-dir'),
    'list-str': ['single-dir'],
    'list-Path': [Path('single-dir')],
    'set-str': {'single-dir'},
    'set-Path': {Path('single-dir')},
}
@pytest.mark.repo_dirs('single-dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_args_single_dir(repo, variant):
    """
    Single directory across types.
    """
    Path('single-dir/file').touch()

    # test
    repo.add(variant)
    assert Path('single-dir/file') in repo.files_staged


variants = {  # pyre-ignore[9]
    'list-str': ['one', 'two', 'three'],
    'list-Path': [Path('one'), Path('two'), Path('three')],
    'list-mixed': ['one', Path('two'), 'three'],
    'set-str': {'one', 'two', 'three'},
    'set-Path': {Path('one'), Path('two'), Path('three')},
    'set-mixed': {Path('one'), 'two', Path('three')},
}
@pytest.mark.repo_dirs('one', 'two', 'three')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_args_multi_dir(repo, variant):
    """
    Multiple directories across types.
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


variants = {  # pyre-ignore[9]
    'top': {'dirs': 'r', 'num': 4},
    'deep': {'dirs': 'r/e/c/u/r/s/i/v/e', 'num': 2},
    'overlap-same': {'dirs': ['r/e/c/u/r', 'r/e/c/u/r/s/i/v/e'], 'num': 2},
    'overlap-more': {'dirs': ['r/e', 'r/e/c/u/r/s/i/v/e'], 'num': 4},
}
@pytest.mark.repo_dirs('r/e/c/u/r/s/i/v/e')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_dir_recursive(repo, variant):
    """
    Recursive directories
    """
    Path('r/e/c/child-r-A').touch()
    Path('r/e/c/child-r-B').touch()
    Path('r/e/c/u/r/s/i/v/e/child-r-A').touch()
    Path('r/e/c/u/r/s/i/v/e/child-r-B').touch()

    # test
    repo.add(variant['dirs'])
    assert variant['num'] == len(repo.files_staged)


variants = {
    'single': ['o n e'],
    'multi': ['o n e', 't w o', 'd i r/t h r e e'],
}
@pytest.mark.repo_dirs('d i r')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_spaces(repo, variant):
    """
    Spaces.
    """
    Path('o n e').touch()
    Path('t w o').touch()
    Path('d i r/t h r e e').touch()

    # test
    repo.add(variant)
    for i in variant:
        assert Path(i) in repo.files_staged
    assert len(variant) == len(repo.files_staged)


def test_add_repeat(repo):
    """
    Repeated target paths are OK.
    """
    Path('repeat-one').touch()
    Path('two').touch()
    Path('three').touch()

    # test
    repo.add(['repeat-one', 'two', 'repeat-one', 'three'])
    assert Path('repeat-one') in repo.files_staged
    assert Path('two') in repo.files_staged
    assert Path('three') in repo.files_staged


variants = {
    'file': 'unchanged-file',
    'dir': 'unchanged-dir',
    'mixed': ['unchanged-file', 'unchanged-dir'],
}
@pytest.mark.repo_dirs('unchanged-dir')
@pytest.mark.repo_files('unchanged-file')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_unchanged(repo, variant):
    """
    Unchanged targets.
    """
    repo.add(variant)
    assert not repo.files_staged


variants = {
    'root': ['one', 'not-exist', 'dir/three'],
    'subdir': ['one', 'two', 'dir/not-exist'],
}
@pytest.mark.repo_dirs('dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_add_not_exist(repo, variant):
    """
    Targets that don't exist.
    """
    Path('one').touch()
    Path('two').touch()
    Path('dir/three').touch()

    # test
    with pytest.raises(FileNotFoundError):
        repo.add(variant)
    assert not repo.files_staged
