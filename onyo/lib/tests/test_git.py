"""Tests for onyo's git module."""
import subprocess
from pathlib import Path

import pytest

from onyo.lib.exceptions import OnyoInvalidRepoError
from onyo.lib.git import GitRepo

# TODO: Alternative approach to fixture:
#       class that defines a setup via literals;
#       parameterize fixture(!!) with these instances;
#       or pytest_generate_tests -> p.66-69


def test_GitRepo_instantiation(tmp_path: Path) -> None:
    """Instantiate and set the root correctly for paths to existing repositories."""

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


def test_GitRepo_init_without_reinit(tmp_path: Path) -> None:
    root = tmp_path / 'doesnotexist'

    # Can initialize a git repository in
    # not yet existing dir:
    gr = GitRepo(root)
    assert not root.exists()
    gr.init_without_reinit()
    assert root.is_dir()
    assert (root / '.git').exists()

    # Re-execution doesn't raise:
    gr.init_without_reinit()


def test_GitRepo_find_root(tmp_path: Path) -> None:
    """``find_root()`` discovers the repo root correctly.

    Both when passed the root itself and subdirectories of a repository.

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


def test_GitRepo_clear_cache(gitrepo) -> None:
    """``clear_cache()`` empties the cache of GitRepo.

    So that an invalid cache can be re-loaded by a new call of the property.
    """
    # create+add a file so it is cached in the gitrepo.files
    file = gitrepo.root / 'asset_for_test.0'
    file.touch()
    gitrepo.commit(file, message="Create file for test")
    assert file in gitrepo.files

    # delete the file (with a non-onyo function to invalid the cache) and then
    # verify that the file stays in the cache after the deletion
    Path.unlink(file)
    subprocess.run(['git', 'add', str(file)], check=True, cwd=gitrepo.root)
    subprocess.run(['git', 'commit', '-m', "Delete file for test"], check=True, cwd=gitrepo.root)
    assert file in gitrepo.files
    assert not file.exists()

    # test GitRepo.clear_cache() fixes the cache
    gitrepo.clear_cache()
    assert file not in gitrepo.files


def test_GitRepo_is_clean_worktree(gitrepo) -> None:
    """``is_clean_worktree()`´ returns ``True`` when the worktree is clean and ``False`` otherwise.

    Changed, staged, and untracked files return ``False``.
    """
    test_file = gitrepo.root / "test_file.txt"

    # initially clean
    assert gitrepo.is_clean_worktree()

    # a file created but not added (i.e. untracked) must lead to return False
    test_file.touch()
    assert not gitrepo.is_clean_worktree()

    # a file added but not commit-ed (i.e. staged) must lead to return False
    subprocess.run(['git', 'add', str(test_file)], check=True, cwd=gitrepo.root)
    assert not gitrepo.is_clean_worktree()

    # when commit-ed, the function must return True again
    subprocess.run(['git', 'commit', '-m', 'commit-ed!'], check=True, cwd=gitrepo.root)
    assert gitrepo.is_clean_worktree()

    # a file modified but not commit-ed (i.e. changed) must lead to return False
    test_file.open('w').write('Test: content')
    subprocess.run(['git', 'add', str(test_file)], check=True, cwd=gitrepo.root)
    assert not gitrepo.is_clean_worktree()

    # when commit-ed, the function must return True again
    subprocess.run(['git', 'commit', '-m', 'commit-ed again!'], check=True, cwd=gitrepo.root)
    assert gitrepo.is_clean_worktree()

    gitignore = gitrepo.root / ".gitignore"
    gitignore.write_text("*.some")
    subprocess.run(['git', 'add', str(gitignore)], check=True, cwd=gitrepo.root)
    subprocess.run(['git', 'commit', '-m', 'add gitignore'], check=True, cwd=gitrepo.root)

    assert gitrepo.is_clean_worktree()
    # Untracked, but gitignore'd file is still clean:
    (gitrepo.root / "ignore.some").touch()
    assert gitrepo.is_clean_worktree()


def test_GitRepo_is_git_path(gitrepo) -> None:
    """``is_git_path()`` identifies git paths.

    Such as ``.git/*``, ``.gitignore``, ``.gitattributes``, ``.gitmodules``, etc.
    """
    directory = gitrepo.root / 'existing' / 'directory'
    directory.mkdir(parents=True, exist_ok=True)
    test_file = directory / "test_file.txt"
    test_file.touch()

    # Test the examples listed above:
    assert gitrepo.is_git_path(gitrepo.root / ".git")
    assert gitrepo.is_git_path(gitrepo.root / ".git" / "HEAD")
    assert gitrepo.is_git_path(gitrepo.root / ".git" / "doesnotexist")
    assert gitrepo.is_git_path(gitrepo.root / ".gitignore")
    assert gitrepo.is_git_path(gitrepo.root / ".gitdoesnotexist")
    assert gitrepo.is_git_path(gitrepo.root / "existing" / ".gitattributes")

    # Must return False
    assert not gitrepo.is_git_path(gitrepo.root)
    assert not gitrepo.is_git_path(gitrepo.root / ".onyo")
    assert not gitrepo.is_git_path(gitrepo.root / "existing")
    assert not gitrepo.is_git_path(gitrepo.root / "existing" / "git_no_.git")
    assert not gitrepo.is_git_path(test_file)


def test_GitRepo_commit(gitrepo) -> None:
    """`GitRepo.commit()` must commit all staged changes.

    This test follows the scheme of `test_GitRepo_add()`.
    """
    test_file = gitrepo.root / 'test_file.txt'
    test_file.touch()
    assert test_file not in gitrepo.files
    # fresh repo w/ no commit
    assert gitrepo.get_hexsha() is None
    gitrepo.commit(test_file, message="Create file for test")
    hexsha = gitrepo.get_hexsha()
    # created a commit:
    assert hexsha is not None
    # only one commit (HEAD~1 does not exist):
    pytest.raises(ValueError, gitrepo.get_hexsha, 'HEAD~1')
    assert test_file in gitrepo.files

    # modify an existing file, and add it
    test_file.open('w').write('Test: content')
    gitrepo.commit(test_file, "Test commit message")
    assert hexsha == gitrepo.get_hexsha('HEAD~1')
    assert test_file in gitrepo.files


@pytest.mark.gitrepo_contents((Path('some.file'),
                               "some content"),
                              (Path('top') / 'mid' / "another.txt",
                               "")
                              )
def test_GitRepo_get_files(gitrepo) -> None:
    # add an untracked files:
    for d in gitrepo.test_annotation['directories']:
        untracked = d / "untracked"
        untracked.touch()

    # only returns tracked files underneath the given directory:
    for d in gitrepo.test_annotation['directories']:
        tree = gitrepo.get_files([d])
        assert [p for p in gitrepo.test_annotation['files'] if d in p.parents] == tree

    # defaults to the entire worktree:
    assert [p for p in gitrepo.test_annotation['files']] == gitrepo.get_files()

    # several dirs:
    if len(gitrepo.test_annotation['directories']) > 1:
        dirs = gitrepo.test_annotation['directories'][:2]
        expected = [p
                    for p in gitrepo.test_annotation['files']
                    if any(d in dirs for d in p.parents)]
        tree = gitrepo.get_files(dirs)
        assert expected == tree


def test_GitRepo_get_hexsha(gitrepo) -> None:
    import string

    # empty repo yields no hexsha:
    assert gitrepo.get_hexsha() is None
    # unknown commit-ish raises ValueError:
    pytest.raises(ValueError, gitrepo.get_hexsha, "DOESNOTEXIST")

    (gitrepo.root / "something").touch()
    subprocess.run(['git', 'add', 'something'], cwd=gitrepo.root)
    subprocess.run(['git', 'commit', '-m', 'some content'], cwd=gitrepo.root)

    # There actually is a commit now:
    sha = gitrepo.get_hexsha()
    assert isinstance(sha, str)
    # full sha is always returned
    assert len(sha) == 40
    # only hex characters used
    assert all(c in string.hexdigits for c in sha)

    # Default is HEAD
    assert sha == gitrepo.get_hexsha('HEAD')

    # New commit:
    (gitrepo.root / "something").write_text("modified")
    subprocess.run(['git', 'add', 'something'], cwd=gitrepo.root)
    subprocess.run(['git', 'commit', '-m', 'changed content'], cwd=gitrepo.root)

    assert sha != gitrepo.get_hexsha("HEAD")
    assert sha == gitrepo.get_hexsha("HEAD~1")


def test_GitRepo_get_commit_msg(gitrepo) -> None:
    # Note: message formatted to make 'equal' comparison
    # straight-forward, including to end with an empty line.
    message = """some random stuff

oncdisabbca
a393a9rjadm----

"""

    # empty repo does not have a commit w/ message yet:
    # TODO: Proper error. ValueError for 'HEAD'? Just return None?
    pytest.raises(subprocess.CalledProcessError, gitrepo.get_commit_msg)

    (gitrepo.root / "something").touch()
    subprocess.run(['git', 'add', 'something'], cwd=gitrepo.root)
    subprocess.run(['git', 'commit', '-m', message], cwd=gitrepo.root)

    # now there is:
    assert message == gitrepo.get_commit_msg()


def test_GitRepo_config(gitrepo) -> None:

    assert gitrepo.get_config("section.name.option") is None
    # TODO: patch env to redirect git config locations
    gitrepo.set_config(key="section.name.option", value="some", location='local')
    git_config = (gitrepo.root / '.git' / 'config').read_text()
    assert "[section \"name\"]" in git_config
    assert "option = some" in git_config
    assert gitrepo.get_config("section.name.option") == "some"

    cfg_file = gitrepo.root / "test_config"
    gitrepo.set_config(key="onyo.test", value="another", location=cfg_file)
    config = cfg_file.read_text()
    assert "[onyo]" in config
    assert "test = another" in config
    assert gitrepo.get_config("onyo.test") is None
    assert gitrepo.get_config("onyo.test", path=cfg_file) == "another"


def test_GitRepo_check_ignore(gitrepo) -> None:
    committed = gitrepo.root / 'book.pdf'
    committed.touch()
    gitrepo.commit(committed, "Add a pdf")

    ignore_file = gitrepo.root / 'some'
    ignore_file.write_text("*.pdf\nsub/\n")
    gitignore = gitrepo.root / '.gitignore'
    gitignore.write_text('*.txt\n')

    paths_to_test = [gitrepo.root / 'some.pdf',
                     gitrepo.root / 'some',
                     gitrepo.root / 'text.txt',
                     gitrepo.root / '.gitignore',
                     gitrepo.root / 'sub' / 'something',
                     committed]
    excluded = gitrepo.check_ignore(ignore=ignore_file,
                                    paths=paths_to_test)
    assert all(p in excluded for p in paths_to_test if p.name.endswith('.pdf'))
    assert all(p in excluded for p in paths_to_test if gitrepo.root / 'sub' in p.parents)
    assert all(p not in excluded for p in paths_to_test if p.name.endswith('.txt'))

    pytest.raises(subprocess.CalledProcessError, gitrepo.check_ignore,
                  ignore=ignore_file, paths=[Path('/') / 'outside' / 'sub' / 'file'])
