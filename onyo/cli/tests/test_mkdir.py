import subprocess
from pathlib import Path

import pytest

from onyo.lib.onyo import OnyoRepo

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
    r"""
    Test that `onyo mkdir <dir>` creates new directories correctly for different
    depths and directory names.
    """
    ret = subprocess.run(['onyo', '--yes', 'mkdir', directory], capture_output=True, text=True)

    # verify output
    assert directory in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist
    d = Path(directory)
    while not d.samefile(repo.git.root):
        assert d.is_dir()
        assert (d / ".anchor").is_file()
        d = d.parent

    # verify that the repository is clean
    assert repo.git.is_clean_worktree()


def test_mkdir_multiple_inputs(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo mkdir <dirs>` creates new directories all in one call when
    given a list of inputs.
    """
    ret = subprocess.run(['onyo', '--yes', 'mkdir', *directories], capture_output=True, text=True)

    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist, and are in output
    for directory in directories:
        assert directory in ret.stdout
        d = Path(directory)
        while not d.samefile(repo.git.root):
            assert d.is_dir()
            assert (d / ".anchor").is_file()
            d = d.parent

    # verify that the repository is clean
    assert repo.git.is_clean_worktree()


def test_mkdir_no_response(repo: OnyoRepo) -> None:
    r"""
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
        d = Path(directory)
        assert not d.is_dir()
        assert not (d / ".anchor").is_file()

    # verify that the repository is clean
    assert repo.git.is_clean_worktree()


def test_mkdir_quiet_flag(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo mkdir --yes --quiet <dirs>` creates new directories without
    printing output.
    """
    ret = subprocess.run(['onyo', '--yes', '--quiet', 'mkdir', *directories],
                         capture_output=True, text=True)

    # verify that all output is empty
    assert not ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify folders and anchors exist
    for directory in directories:
        d = Path(directory)
        while not d.samefile(repo.git.root):
            assert d.is_dir()
            assert (d / ".anchor").is_file()
            d = d.parent

    # verify that the repository is clean
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs(*directories)
@pytest.mark.parametrize('directory', directories)
def test_dir_exists(repo: OnyoRepo, directory: str) -> None:
    r"""
    Test the correct behavior when `onyo mkdir <path>` is called on an
    existing directory.
    """
    ret = subprocess.run(['onyo', 'mkdir', directory], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "already is an inventory directory" in ret.stderr
    assert ret.returncode == 1

    d = Path(directory)
    assert d.is_dir()
    assert (d / ".anchor").is_file()

    # verify that the repository is clean
    assert repo.git.is_clean_worktree()

    # existing non-inventory dir
    regular_dir = repo.git.root / "something new"
    regular_dir.mkdir()
    ret = subprocess.run(['onyo', '--yes', 'mkdir', regular_dir], capture_output=True, text=True)
    assert ret.returncode == 0
    assert regular_dir.is_dir()
    assert (regular_dir / ".anchor").is_file()
    assert repo.is_inventory_dir(regular_dir)
    assert repo.git.is_clean_worktree()


protected_paths = [".anchor",
                   "simple/.git",
                   "simple/.onyo",
                   ".git/nope"
                   ".onyo/nope",
                   ]


@pytest.mark.repo_dirs("simple")
@pytest.mark.parametrize('protected_path', protected_paths)
def test_dir_protected(repo: OnyoRepo, protected_path: str) -> None:
    r"""
    Test the correct error behavior of `onyo mkdir <path>` on protected paths.
    """
    ret = subprocess.run(["onyo", "mkdir", protected_path], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert f"{protected_path} is not a valid inventory path" in ret.stderr
    assert ret.returncode == 1

    # verify that the directory was not created and the repository is clean
    assert not Path(protected_path).is_dir()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs("simple")
def test_mkdir_relative_path(repo: OnyoRepo) -> None:
    r"""
    Test `onyo mkdir <path>` with a relative path given as input.
    """
    ret = subprocess.run(["onyo", "--yes", "mkdir", "simple/../relative"], capture_output=True, text=True)

    # verify output
    assert "relative" in ret.stdout
    assert not ret.stderr
    assert ret.returncode == 0

    # verify that the correct directory was created and the repository is clean
    assert Path("./relative").exists()
    assert not Path('simple/\\.\\./relative').exists()
    assert repo.git.is_clean_worktree()
