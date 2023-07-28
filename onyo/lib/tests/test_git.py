from pathlib import Path
import subprocess

import pytest
from onyo import OnyoInvalidRepoError
from onyo.lib.git import GitRepo


def test_GitRepo_instantiation(tmp_path: Path) -> None:
    """
    The `GitRepo` class must instantiate and set the root correctly for paths
    to existing repositories.
    """
    # initialize the temp_path as an git repository
    subprocess.run(['git', 'init', tmp_path])

    # test that `GitRepo()` instantiates (and sets the root to) the object
    # correctly
    new_repo = GitRepo(tmp_path)
    assert new_repo.root.samefile(tmp_path)

    # create a sub-directory to test the find-root behavior
    subprocess.run(['mkdir', '-p', tmp_path / "sub-directory"])

    # with `find_root=False` it excepts other existing paths e.g. sub-dirs
    new_repo = GitRepo(tmp_path / "sub-directory", find_root=False)
    assert new_repo.root.samefile(tmp_path / "sub-directory")

    # with `find_root=True` it must find the root and set it appropriately
    new_repo = GitRepo(tmp_path / "sub-directory", find_root=True)
    assert new_repo.root.samefile(tmp_path)


def test_GitRepo_find_root(tmp_path: Path) -> None:
    """
    `GitRepo.find_root()` MUST identify the root of a repository for the root
    itself and sub-directories of a repository.
    If called on a Path which is not a git repository it must raise an
    `OnyoInvalidRepoError`.
    """

    # test GitRepo.find_root() with an existing but non-repo path raises the
    # expected OnyoInvalidRepoError
    with pytest.raises(OnyoInvalidRepoError):
        GitRepo.find_root(tmp_path)

    # Path GitRepo.find_root() with a Path that does not exist at all raises the
    # correct OnyoInvalidRepoError
    with pytest.raises(OnyoInvalidRepoError):
        GitRepo.find_root(Path("This/path/does/not/exist"))

    # initialize a new git repo to test correct behavior when git exists
    subprocess.run(['git', 'init', tmp_path])
    subprocess.run(['mkdir', '-p', tmp_path / 'existing/directory'])

    # test that `GitRepo.find_root(root)` returns the same root path
    assert GitRepo.find_root(tmp_path).samefile(tmp_path)

    # test that `GitRepo.find_root()` returns correct root for a sub-directory
    assert GitRepo.find_root(tmp_path / 'existing/directory').samefile(tmp_path)

    # test that `GitRepo.find_root()` raises the correct error when called on
    # a non-existing sub-path under an existing root
    with pytest.raises(OnyoInvalidRepoError):
        GitRepo.find_root(tmp_path / 'non-existing/directory')
