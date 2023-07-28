from pathlib import Path
import subprocess

import pytest
from onyo import OnyoRepo, OnyoInvalidRepoError
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


@pytest.mark.repo_dirs('existing/directory')
def test_GitRepo_instantiation_find_root(repo: OnyoRepo) -> None:
    """
    The GitRepo class must instantiate correctly with paths to sub-directories
    in a repository when `find_root=True`.
    """
    new_repo = GitRepo(repo.git.root / 'existing/directory', find_root=True)
    assert new_repo.root.samefile(repo.git.root)
    assert (new_repo.root / '.git').exists()
