from pathlib import Path
import subprocess
from subprocess import CalledProcessError

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


def test_GitRepo_restore_staged(tmp_path: Path) -> None:
    """
    `GitRepo.restore_staged()` must restore all staged files in the repository.
    If no files are staged, it should not raise an error.
    If there are modified or untracked files, they should not be changed.
    """
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    test_file = new_git.root / 'asset_for_test.0'
    test_file.touch()
    new_git.stage_and_commit(test_file, message="Create file for test")

    # test that no error is raised, when called on a clean repository
    new_git.restore_staged()
    assert new_git.is_clean_worktree()

    # have an untracked, a changed and a staged file
    untracked_file = new_git.root / 'asset_for_test.1'
    untracked_file.touch()

    changed_file = new_git.root / 'asset_for_test.2'
    changed_file.touch()
    new_git.stage_and_commit(changed_file, message="Create file to change")
    changed_file.open('w').write('Test: content')

    test_file.open('w').write('Test: content')
    new_git.add(test_file)
    assert untracked_file in new_git.files_untracked
    assert changed_file in new_git.files_changed
    assert test_file in new_git.files_staged

    # call restore_staged() and verify that the changes on test_file are not
    # staged anymore, but that modified and untracked files are unchanged
    new_git.restore_staged()
    assert test_file not in new_git.files_staged
    assert untracked_file in new_git.files_untracked
    assert changed_file in new_git.files_changed


def test_GitRepo_restore(tmp_path: Path) -> None:
    """
    `GitRepo.restore()` receives a list of paths and must restore changes for
    them.

    This does restore files which contain changes, but it does not restore
    changes that are already staged.
    When called on an untracked file, it must raise an error (like `git restore
    <untracked>`).
    """
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    test_file = new_git.root / 'asset_for_test.0'
    test_file.touch()
    new_git.stage_and_commit([test_file], message="Test File")

    # Test that no error is raised, when called on a clean file
    new_git.restore(test_file)
    assert new_git.is_clean_worktree()

    # Test that calling `GitRepo.restore()` on a file with already staged
    # changes does not effect the file
    test_file.open('w').write('Test: content')
    new_git.add(test_file)
    assert test_file in new_git.files_staged
    new_git.restore(test_file)
    assert test_file in new_git.files_staged

    # Test that calling `GitRepo.restore()` on an untracked file must raise an
    # error (like `git restore` does)
    untracked_file = new_git.root / 'asset_for_test.untracked'
    untracked_file.touch()
    assert untracked_file in new_git.files_untracked
    with pytest.raises(CalledProcessError):
        new_git.restore(untracked_file)
    assert untracked_file in new_git.files_untracked

    # Test that calling `GitRepo.restore()` on a file with unstaged changes
    # restores the file
    changed_file = new_git.root / 'asset_for_test.changed'
    changed_file.touch()
    new_git.stage_and_commit([changed_file], message="Test File")
    changed_file.open('w').write('Test: content')
    assert changed_file in new_git.files_changed
    new_git.restore(changed_file)
    assert changed_file not in new_git.files_changed
    assert changed_file not in new_git.files_untracked
    assert changed_file not in new_git.files_staged


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
    assert test_file in new_git.files_untracked
    assert not new_git.is_clean_worktree()

    # a file added but not commit-ed (i.e. staged) must lead to return False
    new_git.add(test_file)
    assert test_file in new_git.files_staged
    assert not new_git.is_clean_worktree()

    # when commit-ed, the function must return True again
    new_git.commit(test_file, 'commit-ed!')
    assert new_git.is_clean_worktree()

    # a file modified but not commit-ed (i.e. changed) must lead to return False
    test_file.open('w').write('Test: content')
    new_git.add(test_file)
    assert test_file in new_git.files_staged
    assert not new_git.is_clean_worktree()

    # when commit-ed, the function must return True again
    new_git.commit(test_file, 'commit-ed again!')
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


def test_GitRepo_add(tmp_path: Path) -> None:
    """
    `GitRepo.add()` must allow to add files which are either new or contain
    changes. If called on files without changes, it does not raise an error.
    """
    # setup the repo and GitRepo object
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)

    # create a file for the test and add it to git
    existing_file = new_git.root / 'test_file.txt'
    existing_file.touch()
    new_git.stage_and_commit(existing_file, message="Create file for test")

    # create a Path to a file that does not yet exist
    new_file = new_git.root / 'new_file.txt'

    # test that GitRepo.add() does not raise an error on files that exist and
    # have no changes
    new_git.add(existing_file)
    assert new_git.is_clean_worktree()

    # test that GitRepo.add() raises a FileNotFoundError for `new_file`, an
    # absolute path to a file that do not yet exist
    with pytest.raises(FileNotFoundError):
        new_git.add(new_file)

    # modify an existing file, and create a new file
    existing_file.open('w').write('Test: content')
    assert existing_file in new_git.files_changed
    new_file.touch()
    assert new_file in new_git.files_untracked

    new_git.add([existing_file, new_file])
    assert existing_file in new_git.files_staged
    assert new_file in new_git.files_staged

    # after files are `GitRepo.add()`ed they should not be cached in the
    # properties GitRepo.files_changed and GitRepo.files_untracked
    assert existing_file not in new_git.files_changed
    assert new_file not in new_git.files_untracked


def test_GitRepo_commit(tmp_path: Path) -> None:
    """
    `GitRepo.commit()` must commit all staged changes.

    This test follows the scheme of `test_GitRepo_add()`.
    """
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    test_file = new_git.root / 'test_file.txt'
    test_file.touch()
    new_git.stage_and_commit(test_file, message="Create file for test")

    # test that GitRepo.commit() raises a ValueError if no commit message is
    # provided
    with pytest.raises(ValueError):
        new_git.commit()

    # modify an existing file, and add it
    test_file.open('w').write('Test: content')
    new_git.add(test_file)
    assert test_file in new_git.files_staged

    # commit staged changes
    new_git.commit("Test commit message")
    assert test_file in new_git.files

    # after files are `GitRepo.commit()`ed they should not be cached in the
    # properties GitRepo.files_changed or GitRepo.files_staged anymore
    assert test_file not in new_git.files_changed
    assert test_file not in new_git.files_staged


def test_GitRepo_stage_and_commit(tmp_path: Path) -> None:
    """
    `GitRepo.stage_and_commit()` must allow to add+commit changed files.

    This test follows the scheme of `test_GitRepo_add()`.
    """
    subprocess.run(['git', 'init', tmp_path])
    new_git = GitRepo(tmp_path)
    test_file = new_git.root / 'test_file.txt'

    # add a file
    test_file.open('w').write('Test: content')
    assert test_file in new_git.files_untracked

    # add+commit a changed file
    new_git.stage_and_commit(test_file, "Test commit message")
    assert test_file in new_git.files

    # after files are `GitRepo.stage_and_commit()`ed they should not be cached
    # in the properties GitRepo.files_changed or GitRepo.files_staged
    assert test_file not in new_git.files_untracked
    assert test_file not in new_git.files_changed
    assert test_file not in new_git.files_staged
