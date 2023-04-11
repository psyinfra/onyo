import subprocess
from pathlib import Path

import pytest
from onyo.lib import Repo
from typing import List

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro']

directories = ['.',
               's p a c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'very/very/very/deep'
               ]

assets: List[str] = [f"{d}/{f}.{i}" for f in files
                     for i, d in enumerate(directories)]


@pytest.mark.repo_files(*assets)
def test_tree(repo: Repo) -> None:
    """
    Test that `onyo tree` works without input paths.
    """
    ret = subprocess.run(['onyo', 'tree'], capture_output=True, text=True)

    # verify output
    assert not ret.stderr
    assert ret.returncode == 0

    for d in [d for directory in directories for d in Path(directory).parts]:
        assert d in ret.stdout
    for a in assets:
        assert Path(a).name in ret.stdout


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('directory', directories)
def test_tree_with_directory(repo: Repo, directory: str) -> None:
    """
    Test that `onyo tree DIRECTORY` displays directories correctly.
    """
    ret = subprocess.run(['onyo', 'tree', directory], capture_output=True, text=True)

    # verify output
    assert not ret.stderr
    assert ret.returncode == 0

    for d in Path(directory).parts:
        assert d in ret.stdout
    # check that the other paths are not in output
    for d in [d for dirs in directories for d in Path(dirs).parts
              if d not in Path(dirs).parts and dirs != directory]:
        assert d not in ret.stdout
    for a in [a.name for a in Path(directory).iterdir() if a.name[0] != "."]:
        assert a in ret.stdout


@pytest.mark.repo_files(*assets)
def test_tree_multiple_inputs(repo: Repo) -> None:
    """
    Test that `onyo tree <dirs>` displays all directories when given a list of
    paths in one call.
    """
    ret = subprocess.run(['onyo', 'tree', *directories], capture_output=True, text=True)

    # verify output
    assert not ret.stderr
    assert ret.returncode == 0
    for d in [d for directory in directories for d in Path(directory).parts]:
        assert d in ret.stdout
    for a in assets:
        assert Path(a).name in ret.stdout


no_directories: List[str] = ["does_not_exist"] + [d + "/subdir"
                                                  for d in directories]
@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('directory', no_directories)
def test_tree_error_dir_does_not_exist(repo: Repo, directory: str) -> None:
    """
    Test the correct error behavior when `onyo tree <path>` is called on
    non-existing directories and sub-directories.
    """
    ret = subprocess.run(['onyo', 'tree', directory], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths are not directories:" in ret.stderr
    assert directory in ret.stderr
    assert ret.returncode == 1


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_tree_error_is_file(repo: Repo, asset: str) -> None:
    """
    Test the correct error behavior when `onyo tree ASSET` is called on assets.
    """
    ret = subprocess.run(['onyo', 'tree', asset], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths are not directories:" in ret.stderr
    assert asset in ret.stderr
    assert ret.returncode == 1


@pytest.mark.repo_files(*assets)
def test_tree_relative_path(repo: Repo) -> None:
    """
    Test `onyo tree <path>` with a relative path given as input.
    """
    ret = subprocess.run(["onyo", "tree", "simple/../s p a c e s"], capture_output=True, text=True)

    # verify output
    assert not ret.stderr
    assert ret.returncode == 0
    assert "s p a c e s" in ret.stdout


@pytest.mark.repo_files(*assets)
def test_tree_error_relative_path_outside_repo(repo: Repo) -> None:
    """
    Test `onyo tree <path>` gives error with a relative path that leads outside
    of the repository.
    """
    ret = subprocess.run(["onyo", "tree", ".."], capture_output=True, text=True)

    # verify output
    assert not ret.stdout
    assert "The following paths are not inside the repository:" in ret.stderr
    assert ret.returncode == 1
