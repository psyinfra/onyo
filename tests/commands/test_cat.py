import os
import subprocess
from pathlib import Path
import pytest
from git import Repo


@pytest.fixture(scope='function', autouse=True)
def change_test_dir(request, monkeypatch):
    test_dir = os.path.join(request.fspath.dirname, 'sandbox/', 'test_cat/')
    Path(test_dir).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(test_dir)


def create_file(name, content):
    """
    Create and populate a file. Then add and commit to git.
    """
    with open(name, 'w') as f:
        f.write(content)

    # add and commit
    repo = Repo('.')
    repo.git.add(name)
    repo.git.commit(m=f'add {name} for tests')


def delete_file(name):
    """
    Git rm a file and commit.
    """
    repo = Repo('.')
    repo.git.rm(name)
    repo.git.commit(m=f'remove {name} for tests')


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_single():
    """
    Test that a single file is cat successfully, and that stdout matches file
    content.
    """
    name = "single"
    content = "---\nRAM:\nSize:\nUSB:\n"
    create_file(name, content)

    ret = subprocess.run(["onyo", "cat", name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content


def test_multiple():
    """
    Test that multiple files are cat successfully, and that stdout matches file
    content.
    """
    name_1 = "one"
    content_1 = "---\nRAM: 1\nSize: 1\nUSB: 1\n"
    create_file(name_1, content_1)

    name_2 = "two"
    content_2 = "---\nRAM: 2\nSize: 2\nUSB: 2\n"
    create_file(name_2, content_2)

    name_3 = "three"
    content_3 = "---\nRAM: 3\nSize: 3\nUSB: 3\n"
    create_file(name_3, content_3)

    ret = subprocess.run(["onyo", "cat", name_1, name_2, name_3], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content_1 + content_2 + content_3


def test_absent_path():
    """
    Test that cat fails for a path that doesn't exist.
    """
    ret = subprocess.run(["onyo", "cat", "absent/path"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


def test_multiple_with_missing():
    """
    Test that cat fails with multiple paths if at least one doesn't exist.
    """
    ret = subprocess.run(["onyo", "cat", "one", "two", "absent/path"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


def test_not_a_file():
    """
    Test that cat fails if path provided not a file.
    """
    ret = subprocess.run(["onyo", "mkdir", "not_a_file/"])
    assert ret.returncode == 0

    ret = subprocess.run(["onyo", "cat", "not_a_file/"], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


def test_with_spaces():
    """
    Test that cat succeeds if filename contains spaces.
    """
    name = "s p a c e s"
    content = "---\nRAM:\nSize:\nUSB:\n"
    create_file(name, content)

    ret = subprocess.run(["onyo", "cat", name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content


def test_nested_with_spaces():
    """
    Test that cat succeeds if multiple filenames contain spaces and if files are
    nested within a directory.
    """
    ret = subprocess.run(["onyo", "mkdir", "nested/"])
    assert ret.returncode == 0

    name_1 = "nested/o n e"
    content_1 = "---\nRAM: 1\nSize: 1\nUSB: 1\n"
    create_file(name_1, content_1)

    name_2 = "nested/t w o"
    content_2 = "---\nRAM: 2\nSize: 2\nUSB: 2\n"
    create_file(name_2, content_2)

    name_3 = "nested/t h r e e"
    content_3 = "---\nRAM: 3\nSize: 3\nUSB: 3\n"
    create_file(name_3, content_3)

    ret = subprocess.run(["onyo", "cat", name_1, name_2, name_3], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content_1 + content_2 + content_3


def test_same_target():
    """
    Test that cat succeeds if the same path is provided more than once.
    """
    name = "same_target"
    content = "---\nRAM:\nSize:\nUSB:\n"
    create_file(name, content)

    ret = subprocess.run(["onyo", "cat", name, name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content + content


def test_no_trailing_newline():
    """
    Test that cat outputs the file content exactly, and doesn't add any newlines
    or other characters.
    """
    name = "no_trailing_newline"
    content = "---\nRAM:\nSize:\nUSB:"
    create_file(name, content)

    ret = subprocess.run(["onyo", "cat", name], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == content


def test_invalid_yaml():
    """
    Test that cat fails for a file with invalid yaml content.
    """
    # create directory
    ret = subprocess.run(["onyo", "mkdir", "invalid_yaml/"])
    assert ret.returncode == 0

    # check that the current repo state is valid (this is technically redundant
    # as mkdir already does an onyo fsck)
    ret = subprocess.run(["onyo", "fsck"], capture_output=True, text=True)
    assert ret.returncode == 0

    # create file with invalid yaml content
    name = "invalid_yaml/bad_yaml"
    content = "I: \nam:bad:\nbad:yaml\n"
    create_file(name, content)

    # check that yaml is invalid
    ret = subprocess.run(["onyo", "fsck"], capture_output=True, text=True)
    assert ret.returncode == 1

    # check that cat fails with invalid yaml content
    ret = subprocess.run(["onyo", "cat", name], capture_output=True, text=True)
    assert ret.returncode == 1
    assert ret.stderr
    assert not ret.stdout

    # clean up invalid file
    delete_file(name)

    # Do another fsck to guarantee that the repo is clean
    ret = subprocess.run(["onyo", "fsck"], capture_output=True, text=True)
    assert ret.returncode == 0
