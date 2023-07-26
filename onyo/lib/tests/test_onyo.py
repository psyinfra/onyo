from pathlib import Path

import pytest
from onyo import OnyoRepo, OnyoInvalidRepoError
from onyo.lib.commands import fsck, mkdir, mv


def test_OnyoRepo_instantiation_existing(repo: OnyoRepo) -> None:
    """
    The OnyoRepo class must instantiate correctly for paths to existing
    repositories.
    """
    new_repo = OnyoRepo(repo.git.root, init=False)
    assert new_repo.git.root.samefile(repo.git.root)


def test_OnyoRepo_instantiation_non_existing(tmp_path: Path) -> None:
    """
    The OnyoRepo class must instantiate correctly for paths to non-existing
    repositories.
    """
    new_repo = OnyoRepo(tmp_path, init=True)
    assert new_repo.git.root.samefile(tmp_path)
    assert (new_repo.git.root / '.onyo').exists()
    fsck(new_repo)


def test_OnyoRepo_incorrect_input_arguments_raise_error(repo: OnyoRepo,
                                                        tmp_path: Path) -> None:
    """
    The OnyoRepo must raise certain errors for invalid or conflicting arguments.
    - raise a OnyoInvalidRepoError when called on a path that is
      not yet a valid onyo repository.
    - raise a `ValueError` when called with conflicting arguments
      `init=True` and `find_root=True`
    - raise a `FileExistsError` when trying to initialize a new OnyoRepo for a
      path that is already an OnyoRepo.
    """
    # try OnyoRepo with a non-repo path
    with pytest.raises(OnyoInvalidRepoError):
        OnyoRepo(tmp_path / 'no-existy', init=False)
    # try OnyoRepo initialization with a path which is already a repo
    with pytest.raises(FileExistsError):
        OnyoRepo(repo.git.root, init=True)
    # try with conflicting argumeents `init=True` and `find_root=True`
    with pytest.raises(ValueError):
        OnyoRepo(repo.git.root, init=True, find_root=True)


@pytest.mark.repo_files('a/test/asset_for_test.0')
def test_clear_caches(repo: OnyoRepo) -> None:
    """
    The function `clear_caches()` must allow to empty the cache of the OnyoRepo,
    so that an invalid cache can be re-loaded by a newly call of the property.
    """
    # make sure the asset is in the cache
    asset = Path('a/test/asset_for_test.0').resolve()
    assert asset in repo.asset_paths

    # delete the asset (with a non-onyo function to invalid the cache) and then
    # verify that the asset stays in the cache after the deletion
    Path.unlink(asset)
    assert asset in repo.asset_paths

    # test clear_caches() fixes the cache
    repo.clear_caches(assets=True)
    assert asset not in repo.asset_paths


def test_Repo_generate_commit_message(repo: OnyoRepo) -> None:
    """
    A generated commit message has to have a header with less then 80 characters
    length, and a body with the paths to changed files and directories relative
    to the root of the repository.
    """
    modified = [repo.git.root / 's p a c e s',
                repo.git.root / 'a/new/folder']

    # modify the repository with some different commands:
    mkdir(repo, modified, quiet=True, yes=True, message=None)
    mv(repo, *modified, quiet=True, yes=True, message=None)

    # generate a commit message:
    message = repo.generate_commit_message(cmd='TST', modified=modified)
    lines = message.splitlines()
    header = lines[0]
    body = "\n".join(lines[1:])

    # root should not be in output
    assert str(repo.git.root) not in message

    # verify all necessary information is in the header:
    assert f'TST [{len(modified)}]: ' in header

    # verify all necessary information is in the body:
    assert 'a/new/folder' in body
    assert 's p a c e s' in body


@pytest.mark.repo_files('a/test/asset_for_test.0')
def test_is_onyo_path(repo: OnyoRepo) -> None:
    """
    Verify that `OnyoRepo.is_onyo_path()` differentiates correctly between
    paths under `.onyo/` and outside of it.
    """
    # True for the directory `.onyo/` itself
    assert repo.is_onyo_path(repo.dot_onyo)
    # True for the directory `templates` inside of `.onyo/`
    assert repo.is_onyo_path(repo.dot_onyo / 'templates')
    # True for a file inside `.onyo/`
    assert repo.is_onyo_path(repo.dot_onyo / 'templates' / 'empty')

    # other files/directories beginning with .onyo should be recognized too
    assert repo.is_onyo_path(repo.git.root / '.onyoignore')

    # False for root of onyo repository
    assert not repo.is_onyo_path(repo.git.root)
    # False for directory `.git/`
    assert not repo.is_onyo_path(repo.git.root / '.git')
    # False for directory inside an onyo repository
    assert not repo.is_onyo_path(repo.git.root / 'a' / 'test')
    # False for asset inside an onyo repository
    assert not repo.is_onyo_path(repo.git.root / 'a' / 'test' / 'asset_for_test.0')
