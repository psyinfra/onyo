import subprocess
from pathlib import Path

import pytest
from onyo.lib import OnyoRepo
from onyo.lib.commands import fsck


directories = ['simple',
               's p a c e s',
               'overlap/one',
               'overlap/two',
               'r/e/c/u/r/s/i/v/e',
               'spe\"cial\\char\'actஞers',
               'very/very/very/deep'
               ]


@pytest.mark.parametrize('directory', directories)
def test_mkdir(repo: OnyoRepo, directory: str) -> None:
    """
    Test that `onyo mkdir <dir>` creates new directories correctly for different
    depths and directory names.
    """
    ret = subprocess.run(['onyo', 'mkdir', '--yes', directory], capture_output=True, text=True)

    # verify output
    assert directory in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist
    d = Path(directory)
    while not d.samefile(repo.git.root):
        assert Path(d).is_dir()
        assert Path(d, ".anchor").is_file()
        d = d.parent

    # verify that the repository is clean
    fsck(repo)


def test_mkdir_multiple_inputs(repo: OnyoRepo) -> None:
    """
    Test that `onyo mkdir <dirs>` creates new directories all in one call when
    given a list of inputs.
    """
    ret = subprocess.run(['onyo', 'mkdir', '--yes', *directories], capture_output=True, text=True)

    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist, and are in output
    for directory in directories:
        assert directory in ret.stdout
        d = Path(directory)
        while not d.samefile(repo.git.root):
            assert Path(d).is_dir()
            assert Path(d, ".anchor").is_file()
            d = d.parent

    # verify that the repository is clean
    fsck(repo)


def test_mkdir_no_response(repo: OnyoRepo) -> None:
    """
    Test that `onyo mkdir <dirs>` creates no new directories when user responds
    with "no".
    """
    ret = subprocess.run(['onyo', 'mkdir', *directories], input='n',
                         capture_output=True, text=True)

    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors were not created, but are mentioned in output
    for directory in directories:
        assert directory in ret.stdout
        assert not Path(directory).is_dir()
        assert not Path(directory, ".anchor").is_file()

    # verify that the repository is clean
    fsck(repo)


def test_mkdir_message_flag(repo: OnyoRepo) -> None:
    """
    Test that `onyo mkdir --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"

    # test `onyo mkdir --message msg`
    ret = subprocess.run(['onyo', 'mkdir', '--yes', '--message', msg, *directories], capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr
    for directory in directories:
        assert directory in ret.stdout

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I', directories[0]], capture_output=True, text=True)
    assert msg in ret.stdout
    fsck(repo)


def test_mkdir_quiet_flag(repo: OnyoRepo) -> None:
    """
    Test that `onyo mkdir --yes --quiet <dirs>` creates new directories without
    printing output.
    """
    ret = subprocess.run(['onyo', 'mkdir', '--yes', '--quiet', *directories],
                         capture_output=True, text=True)

    # verify that all output is empty
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist
    for directory in directories:
        d = Path(directory)
        while not d.samefile(repo.git.root):
            assert Path(d).is_dir()
            assert Path(d, ".anchor").is_file()
            d = d.parent

    # verify that the repository is clean
    fsck(repo)


@pytest.mark.repo_dirs(*directories)
@pytest.mark.parametrize('directory', directories)
def test_error_dir_exists(repo: OnyoRepo, directory: str) -> None:
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
    fsck(repo)


@pytest.mark.repo_files(*directories)  # used as files to test errors
@pytest.mark.parametrize('file', directories)
def test_dir_exists_as_file(repo: OnyoRepo, file: str) -> None:
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
    fsck(repo)


#  Note: I don't think it's necessary to exclude `.anchor` as a directory name,
#  hence deleted ".anchor" from that list for now:
protected_paths = ["simple/.git",
                   "simple/.onyo",
                   ".git/nope"
                   ".onyo/nope",
                   ]


@pytest.mark.repo_dirs("simple")
@pytest.mark.parametrize('protected_path', protected_paths)
def test_dir_protected(repo: OnyoRepo, protected_path: str) -> None:
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
    fsck(repo)


@pytest.mark.repo_dirs("simple")
def test_mkdir_relative_path(repo: OnyoRepo) -> None:
    """
    Test `onyo mkdir <path>` with a relative path given as input.
    """
    ret = subprocess.run(["onyo", "mkdir", "--yes", "simple/../relative"], capture_output=True, text=True)

    # verify output
    assert "relative/.anchor" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the correct directory was created and the repository is clean
    assert Path("./relative").exists()
    assert not Path('simple/\\.\\./relative').exists()
    fsck(repo)
