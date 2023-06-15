from pathlib import Path

import pytest
from onyo import OnyoRepo, OnyoInvalidRepoError
from onyo.lib.commands import fsck


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
    assert (new_repo.git.root / ".onyo").exists()
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
        OnyoRepo(tmp_path / "no-existy", init=False)
    # try OnyoRepo initialization with a path which is already a repo
    with pytest.raises(FileExistsError):
        OnyoRepo(repo.git.root, init=True)
    # try with conflicting argumeents `init=True` and `find_root=True`
    with pytest.raises(ValueError):
        OnyoRepo(repo.git.root, init=True, find_root=True)
