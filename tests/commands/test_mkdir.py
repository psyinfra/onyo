import subprocess
from pathlib import Path

import pytest
from onyo.lib import Repo


directories = ['simple',
               's p a c e s',
               's p a/c e s',
               'overlap/one',
               'overlap/two',
               'overlap/three',
               'r/e/c/u/r/s/i/v/e',
               'spe\"cial\\char\'actஞers',
               'very/very/very/deep'
               ]


@pytest.mark.parametrize('directory', directories)
def test_mkdir(repo: Repo, directory: str) -> None:
    """
    Test that `onyo mkdir <dir>` creates new directories correctly for different
    depths and directory names.
    """
    ret = subprocess.run(['onyo', 'mkdir', directory], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist
    d = Path(directory)
    while not d.samefile(repo.root):
        assert Path(d).is_dir()
        assert Path(d, ".anchor").is_file()
        d = d.parent

    # verify that the repository is clean
    repo.fsck()


def test_mkdir_multiple_inputs(repo: Repo) -> None:
    """
    Test that `onyo mkdir <dirs>` creates new directories all in one call when
    given a list of inputs.
    """
    ret = subprocess.run(['onyo', 'mkdir'] + directories, capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist
    for directory in directories:
        d = Path(directory)
        while not d.samefile(repo.root):
            assert Path(d).is_dir()
            assert Path(d, ".anchor").is_file()
            d = d.parent

    # verify that the repository is clean
    repo.fsck()


def test_mkdir_message_flag(repo: Repo) -> None:
    """
    Test that `onyo mkdir --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"

    # test `onyo mkdir --message msg`
    ret = subprocess.run(['onyo', 'mkdir', '--message', msg, *directories], capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I'], capture_output=True, text=True)
    assert msg in ret.stdout
    repo.fsck()


@pytest.mark.repo_dirs(*directories)
@pytest.mark.parametrize('directory', directories)
def test_error_dir_exists(repo: Repo, directory: str) -> None:
    """
    Test the correct error behavior when `onyo mkdir <path>` is called on an
    existing directory name.
    """
    ret = subprocess.run(['onyo', 'mkdir', directory], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths already exist:" in ret.stderr
    assert ret.returncode == 1

    assert Path(directory).is_dir()
    assert Path(directory, ".anchor").is_file()

    # verify that the repository is clean
    repo.fsck()


@pytest.mark.repo_files(*directories)  # used as files to test errors
@pytest.mark.parametrize('file', directories)
def test_dir_exists_as_file(repo: Repo, file: str) -> None:
    """
    Test the correct error behavior when `onyo mkdir <file>` is called on files.
    """
    ret = subprocess.run(['onyo', 'mkdir', file], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths already exist:" in ret.stderr
    assert ret.returncode == 1

    assert Path(file).is_file()

    # verify that the repository is clean
    repo.fsck()


protected_paths = [".anchor",
                   "simple/.git",
                   "simple/.onyo",
                   ".git/nope"
                   ".onyo/nope",
                   ]
@pytest.mark.repo_dirs("simple")
@pytest.mark.parametrize('protected_path', protected_paths)
def test_dir_protected(repo: Repo, protected_path: str) -> None:
    """
    Test the correct error behavior of `onyo mkdir <path>` on protected paths.
    """
    ret = subprocess.run(["onyo", "mkdir", protected_path], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert 'protected by onyo' in ret.stderr
    assert ret.returncode == 1

    # verify that the directory was not created and the repository is clean
    assert not Path(protected_path).is_dir()
    repo.fsck()


@pytest.mark.repo_dirs("simple")
def test_mkdir_relative_path(repo: Repo) -> None:
    """
    Test `onyo mkdir <path>` with a relative path given as input.
    """
    ret = subprocess.run(["onyo", "mkdir", "simple/../relative"], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the correct directory was created and the repository is clean
    assert Path("./relative").exists()
    assert not Path('simple/\\.\\./relative').exists()
    repo.fsck()
