import subprocess
from pathlib import Path
import pytest
from onyo import OnyoInvalidRepoError

variants = [
    'file',
    'dir/file',
    's p a c e s',
    'd i r/s p a c e s'
]
@pytest.mark.repo_dirs('dir', 'd i r')
@pytest.mark.parametrize('variant', variants)
def test_single(repo, variant):
    """
    Test that a single file is cat successfully, and that stdout matches file
    content.
    """
    name = variant
    content = "---\nRAM:\nSize:\nUSB:\n"

    # add file
    Path(name).write_text(content)
    repo.add(name)
    repo.commit('populate for tests')

    # test
    ret = subprocess.run(["onyo", "cat", name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content


@pytest.mark.repo_dirs('dir')
def test_multiple(repo):
    """
    Test that multiple files are cat successfully, and that stdout matches file
    content.
    """
    name_1 = "one"
    content_1 = "---\nRAM: 1\nSize: 1\nUSB: 1\n"
    name_2 = "dir/two"
    content_2 = "---\nRAM: 2\nSize: 2\nUSB: 2\n"
    name_3 = "t h r e e"
    content_3 = "---\nRAM: 3\nSize: 3\nUSB: 3\n"

    # add files
    Path(name_1).write_text(content_1)
    Path(name_2).write_text(content_2)
    Path(name_3).write_text(content_3)
    repo.add([name_1, name_2, name_3])
    repo.commit('populate for tests')

    # test
    ret = subprocess.run(["onyo", "cat", name_1, name_2, name_3], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content_1 + content_2 + content_3


variants = [
    'does-not-exist',
    'dir/does-not-exist',
    'does/not-exist'
]
@pytest.mark.repo_files('one', 'dir/two')
@pytest.mark.parametrize('variant', variants)
def test_absent_path(repo, variant):
    """
    Test that cat fails for a path that doesn't exist.
    """
    ret = subprocess.run(['onyo', 'cat', variant], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


variants = {  # pyre-ignore[9]
    'first': ['does-not-exist', 'one', 'dir/two'],
    'middle': ['one', 'does-not-exist', 'dir/two'],
    'last': ['one', 'dir/two', 'does-not-exist'],
}
@pytest.mark.repo_files('one', 'dir/two')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_multiple_with_missing(repo, variant):
    """
    Test that cat fails with multiple paths if at least one doesn't exist.
    """
    ret = subprocess.run(['onyo', 'cat'] + variant, capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_dirs('dir')
def test_not_a_file(repo):
    """
    Test that cat fails if path provided not a file.
    """
    ret = subprocess.run(['onyo', 'cat', 'dir'], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


def test_same_target(repo):
    """
    Test that cat succeeds if the same path is provided more than once.
    """
    name = "same_target"
    content = "---\nRAM:\nSize:\nUSB:\n"

    # add file
    Path(name).write_text(content)
    repo.add(name)
    repo.commit('populate for tests')

    # test
    ret = subprocess.run(['onyo', 'cat', name, name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content + content


def test_no_trailing_newline(repo):
    """
    Test that cat outputs the file content exactly, and doesn't add any newlines
    or other characters.
    """
    name = "no_trailing_newline"
    content = "---\nRAM:\nSize:\nUSB:"

    # add file
    Path(name).write_text(content)
    repo.add(name)
    repo.commit('populate for tests')

    # test
    ret = subprocess.run(['onyo', 'cat', name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content


def test_invalid_yaml(repo):
    """
    Test that cat fails for a file with invalid yaml content.
    """
    # create file with invalid yaml content
    name = "bad_yaml"
    content = "I: \nam:bad:\nbad:yaml\n"

    # add file
    Path(name).write_text(content)
    repo.add(name)
    repo.commit('populate for tests')

    # check that yaml is invalid
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['asset-yaml'])

    # test
    ret = subprocess.run(['onyo', 'cat', name], capture_output=True, text=True)
    assert ret.returncode == 1
    assert ret.stderr
    assert not ret.stdout
