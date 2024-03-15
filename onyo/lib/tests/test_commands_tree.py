import pytest

from onyo.lib.inventory import Inventory
from ..commands import onyo_tree

# TODO: test output?


@pytest.mark.ui({'yes': True})
def test_onyo_tree_errors(inventory: Inventory) -> None:
    """`onyo_tree` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'

    # no tree for files
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  dirs=[(str(asset_path), asset_path)])

    # non-existing dir
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  dirs=[(str(dir_path / "doesnotexist"), dir_path / "doesnotexist")])

    # existing dir, but outside of onyo repository
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  dirs=[(str(inventory.root / ".."), inventory.root / "..")])

    # one of many paths invalid
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  dirs=[(str(inventory.root / "somewhere" / "nested"), inventory.root / "somewhere" / "nested"),
                        (str(inventory.root / "doesnotexist"), inventory.root / "doesnotexist"),
                        (str(dir_path), dir_path)])

    # no error scenario leaves the git worktree unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_single(inventory: Inventory,
                          capsys) -> None:
    """Display a tree for a directory."""
    directory_path = inventory.root / "somewhere" / "nested"

    # move an asset and a dir to the same destination
    onyo_tree(inventory,
              dirs=[(str(directory_path), directory_path)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(subtrees=[directory_path]):
        assert all([part in tree_output for part in path.parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_multiple_paths(inventory: Inventory,
                                  capsys) -> None:
    """Display multiple trees with one call."""
    dir_path = inventory.root / 'somewhere' / 'nested'

    onyo_tree(inventory,
              dirs=[(str(dir_path), dir_path),
                    (str(inventory.root), inventory.root)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(subtrees=[dir_path, inventory.root]):
        assert all([part in tree_output for part in path.parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_without_explicit_paths(inventory: Inventory,
                                          capsys) -> None:
    """Display the root of the inventory, if onyo_tree() is called without paths."""
    onyo_tree(inventory)

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(subtrees=[inventory.root]):
        assert all([part in tree_output for part in path.relative_to(inventory.root).parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_relative_single(inventory: Inventory,
                                   capsys) -> None:
    """Display a tree for a relative subdirectory."""
    directory_path = inventory.root / "somewhere" / "nested"

    # move an asset and a dir to the same destination
    onyo_tree(inventory,
              dirs=[("somewhere/nested", directory_path)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(subtrees=[directory_path]):
        assert all([part in tree_output for part in path.relative_to(inventory.root).parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_errors_before_showing_trees(inventory: Inventory) -> None:
    """`onyo_tree` must raise the correct error if one of the paths does not exist."""
    directory_path = inventory.root / "somewhere" / "nested"
    non_existing_path = inventory.root / "doesnotexist"

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  dirs=[(str(directory_path), directory_path),
                        (str(non_existing_path), non_existing_path),
                        (str(inventory.root), inventory.root)])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.repo_dirs("a/b/c", "a/d/c")
def test_onyo_tree_with_same_dir_twice(inventory: Inventory,
                                       capsys) -> None:
    """Allow to display the tree to a directory twice when
    `onyo_tree()` is called with the same path twice at once."""
    directory_path = inventory.root / "somewhere" / "nested"

    # call onyo_tree() with `directory_path` twice in `paths`.
    onyo_tree(inventory,
              dirs=[(str(directory_path), directory_path),
                    (str(inventory.root), inventory.root),
                    (str(directory_path), directory_path)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(subtrees=[directory_path]):
        assert all([part in tree_output for part in path.parts])
    assert tree_output.count(str(directory_path)) == 2
    assert inventory.repo.git.is_clean_worktree()
