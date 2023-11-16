import subprocess
from pathlib import Path

import pytest

from onyo import OnyoInvalidRepoError
from onyo.lib.git import GitRepo


def test_GitRepo_instantiation(tmp_path: Path) -> None:
    """
    The `GitRepo` class must instantiate and set the root correctly for paths
    to existing repositories.
    """
    # initialize the temp_path as a git repository
    subprocess.run(['git', 'init', tmp_path])

    # test that `GitRepo()` instantiates (and sets the root to) the object
    # correctly
    new_repo = GitRepo(tmp_path)
    assert new_repo.root.samefile(tmp_path)

    # create a sub-directory to test the find-root behavior
    subprocess.run(['mkdir', '-p', tmp_path / "sub-directory"])

    # with `find_root=False` it accepts other existing paths e.g. sub-dirs
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
    new_git.commit(file, message="Create file for test")
    assert file in new_git.files

    # delete the file (with a non-onyo function to invalid the cache) and then
    # verify that the file stays in the cache after the deletion
    Path.unlink(file)
    subprocess.run(['git', 'add', str(file)], check=True, cwd=new_git.root)
    subprocess.run(['git', 'commit', '-m', "Delete file for test"], check=True, cwd=new_git.root)
    assert file in new_git.files
    assert not file.exists()

    # test GitRepo.clear_caches() fixes the cache
    new_git.clear_caches(files=True)
    assert file not in new_git.files


def test_GitRepo_is_clean_worktree(tmp_path: Path) -> None:
    """
    `GitRepo.is_clean_worktree()´ must return True when the worktree is clean,
    and otherwise (i.e. for changed, staged, and unstracked files) return False.
    """
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    test_file = new_git.root / "test_file.txt"

    # initially clean
    assert new_git.is_clean_worktree()

    # a file created but not added (i.e. untracked) must lead to return False
    test_file.touch()
    assert not new_git.is_clean_worktree()

    # a file added but not commit-ed (i.e. staged) must lead to return False
    subprocess.run(['git', 'add', str(test_file)], check=True, cwd=new_git.root)
    assert not new_git.is_clean_worktree()

    # when commit-ed, the function must return True again
    subprocess.run(['git', 'commit', '-m', 'commit-ed!'], check=True, cwd=new_git.root)
    assert new_git.is_clean_worktree()

    # a file modified but not commit-ed (i.e. changed) must lead to return False
    test_file.open('w').write('Test: content')
    subprocess.run(['git', 'add', str(test_file)], check=True, cwd=new_git.root)
    assert not new_git.is_clean_worktree()

    # when commit-ed, the function must return True again
    subprocess.run(['git', 'commit', '-m', 'commit-ed again!'], check=True, cwd=new_git.root)
    assert new_git.is_clean_worktree()


@pytest.mark.repo_files('existing/directory/test_file.txt')
def test_GitRepo_is_git_path(tmp_path: Path) -> None:
    """
    `GitRepo.is_git_path()` needs to identify and return True for `.git/*`,
    `.gitignore`, `.gitattributes`, `.gitmodules`, etc., and otherwise return
    False.
    """
    subprocess.run(['git', 'init', tmp_path])
    subprocess.run(['mkdir', '-p', tmp_path / 'existing' / 'directory' /
                    'test_file.txt'])
    new_git = GitRepo(tmp_path)

    # Test the examples listed above:
    assert new_git.is_git_path(new_git.root / ".git")
    assert new_git.is_git_path(new_git.root / ".git" / "HEAD")
    assert new_git.is_git_path(new_git.root / ".git" / "doesnotexist")
    assert new_git.is_git_path(new_git.root / ".gitignore")
    assert new_git.is_git_path(new_git.root / ".gitdoesnotexist")
    assert new_git.is_git_path(new_git.root / "existing" / ".gitattributes")

    # Must return False
    assert not new_git.is_git_path(new_git.root)
    assert not new_git.is_git_path(new_git.root / ".onyo")
    assert not new_git.is_git_path(new_git.root / "existing")
    assert not new_git.is_git_path(new_git.root / "existing" / "git_no_.git")
    assert not new_git.is_git_path(new_git.root / "existing" / "directory" /
                                   "test_file.txt")


def test_GitRepo_commit(tmp_path: Path) -> None:
    """
    `GitRepo.commit()` must commit all staged changes.

    This test follows the scheme of `test_GitRepo_add()`.
    """
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    test_file = new_git.root / 'test_file.txt'
    test_file.touch()
    assert test_file not in new_git.files
    # fresh repo w/ no commit
    assert new_git.get_hexsha() is None
    new_git.commit(test_file, message="Create file for test")
    hexsha = new_git.get_hexsha()
    # created a commit:
    assert hexsha is not None
    # only one commit (HEAD~1 does not exist):
    pytest.raises(ValueError, new_git.get_hexsha, 'HEAD~1')
    assert test_file in new_git.files

    # modify an existing file, and add it
    test_file.open('w').write('Test: content')
    new_git.commit(test_file, "Test commit message")
    assert hexsha == new_git.get_hexsha('HEAD~1')
    assert test_file in new_git.files
