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


def test_GitRepo_clear_caches(tmp_path: Path) -> None:
    """
    The function `GitRepo.clear_caches()` must allow to empty the cache of the
    GitRepo, so that an invalid cache can be re-loaded by a new call of the
    property.
    """
    # initialize and instantiate `GitRepo`, and create+add a file so it is
    # cached in the new_git.files
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    file = new_git.root / 'asset_for_test.0'
    file.touch()
    new_git.stage_and_commit(file, message="Create file for test")
    assert file in new_git.files

    # delete the file (with a non-onyo function to invalid the cache) and then
    # verify that the file stays in the cache after the deletion
    Path.unlink(file)
    new_git.stage_and_commit(file, message="Delete file for test")
    assert file in new_git.files
    assert not file.exists()

    # test GitRepo.clear_caches() fixes the cache
    new_git.clear_caches(files=True)
    assert file not in new_git.files
