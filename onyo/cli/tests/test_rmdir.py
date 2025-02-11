from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from onyo.lib.items import Item


assets = [
    Item({
        "type": "type",
        "make": "make",
        "model.name": "model",
        "serial": "001",
        "onyo.is.directory": True,
        "onyo.path.relative": Path("subdir") / "type_make_model.001",
    }),
    Item({
        "type": "type",
        "make": "make",
        "model.name": "model",
        "serial": "002",
        "onyo.is.directory": True,
        "onyo.path.relative": Path("subdir") / "type_make_model.002",
    }),
    Item({
        "type": "type",
        "make": "make",
        "model.name": "model",
        "serial": "003",
        "onyo.is.directory": False,
        "onyo.path.relative": Path("subdir") / "type_make_model.003",
    }),
    Item({
        "type": "type",
        "make": "make",
        "model.name": "model",
        "serial": "004",
        "onyo.is.directory": False,
        "onyo.path.relative": Path("subdir") / "type_make_model.004",
    }),
]
directories = [
    Path('one'),
    Path('s p a c e s'),
    Path('r/e/c/u/r/s/i/v/e'),
    Path('overlap/alpha'),
    Path('overlap/beta'),
    Path('subdir/type_make_model.001/subdir'),
]
directories_without_asset_subdirectories = [d for d in directories if all([False for a in assets if a['onyo']['path']['relative'] in d.parents])]

@pytest.mark.inventory_assets(*assets)
@pytest.mark.inventory_dirs(*directories)
@pytest.mark.parametrize('directory', directories)
def test_rmdir_single_input(onyorepo,
                            directory: Path) -> None:
    r"""Delete a single directory.

    ``onyo rmdir DIRECTORY``
    """

    ret = subprocess.run(['onyo', '--yes', 'rmdir', str(directory)],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed directories:" in ret.stdout
    assert str(directory) in ret.stdout
    assert not ret.stderr

    # delete was successful
    assert not directory.exists()

    # other directories are untouched
    for d in [x for x in directories if x != directory]:
        assert d.exists()

    # repository is clean
    assert onyorepo.git.is_clean_worktree()


@pytest.mark.inventory_assets(*assets)
@pytest.mark.inventory_dirs(*directories)
def test_rmdir_multiple_inputs(onyorepo) -> None:
    r"""Delete multiple directories at once.

    ``onyo rmdir DIRECTORY DIRECTORY``
    """

    ret = subprocess.run(['onyo', '--yes', 'rmdir', *directories],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Removed directories:" in ret.stdout
    for d in directories:
        assert str(d) in ret.stdout
    assert not ret.stderr

    # delete was successful
    for d in directories:
        # target was deleted
        assert not d.exists()
        # parent is untouched
        assert d.parent.exists()

    # repository is clean
    assert onyorepo.git.is_clean_worktree()


@pytest.mark.inventory_assets(*assets)
@pytest.mark.inventory_dirs(*directories)
def test_rmdir_error_non_empty(onyorepo) -> None:
    r"""Error on non-empty directories."""

    # apologies for the hardcoded list
    non_empty_dirs = [
        Path('r/'),
        Path('r/e/'),
        Path('r/e/c/'),
        Path('r/e/c/u/'),
        Path('r/e/c/u/r/'),
        Path('r/e/c/u/r/s/'),
        Path('r/e/c/u/r/s/i/'),
        Path('r/e/c/u/r/s/i/v/'),
        Path('overlap/'),
        Path('subdir/'),
        Path('subdir/type_make_model.001/'),
    ]

    for d in non_empty_dirs:
        ret = subprocess.run(['onyo', '--yes', 'rmdir', d],
                             capture_output=True, text=True)

        assert ret.stderr
        assert ret.returncode == 1

        # directory was not deleted, and is mentioned in output
        assert str(d) in ret.stderr
        assert d.is_dir()

    # verify that the repository is clean
    assert onyorepo.git.is_clean_worktree()


@pytest.mark.inventory_assets(*assets)
@pytest.mark.inventory_dirs(*directories_without_asset_subdirectories)
def test_rmdir_convert_asset_dir(onyorepo) -> None:
    r"""Convert Asset Directories into Asset Files."""

    asset_dirs = [a['onyo.path.relative'] for a in onyorepo.test_annotation['assets'] if a.get('onyo.is.directory')]
    ret = subprocess.run(['onyo', '--yes', 'rmdir', *asset_dirs],
                         capture_output=True, text=True)

    assert not ret.stderr
    assert ret.returncode == 0

    # directories were deleted, and are mentioned in output
    for a in asset_dirs:
        assert str(a) in ret.stdout
        assert a.is_file()

    # verify that the repository is clean
    assert onyorepo.git.is_clean_worktree()


@pytest.mark.inventory_assets(*assets)
@pytest.mark.inventory_dirs(*directories)
def test_rmdir_error_on_asset_files(onyorepo) -> None:
    r"""Error on Asset Files."""

    asset_files = [a['onyo.path.relative'] for a in onyorepo.test_annotation['assets'] if not a.get('onyo.is.directory')]
    for a in asset_files:
        ret = subprocess.run(['onyo', '--yes', 'rmdir', str(a)],
                             capture_output=True, text=True)

        assert not ret.stdout
        assert ret.returncode == 1

        # file was not deleted, and is mentioned in output
        assert str(a) in ret.stderr
        assert a.is_file()

    # verify that the repository is clean
    assert onyorepo.git.is_clean_worktree()
