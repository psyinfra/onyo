import pytest

from onyo.lib.inventory import Inventory
from ..commands import onyo_tree

# TODO: test with relativ paths?
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
                  paths=[asset_path])

    # non-existing dir
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[dir_path / "doesnotexist"])

    # existing dir, but outside of onyo repository
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[inventory.root / ".."])

    # one of many paths invalid
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[inventory.root / "somewhere" / "nested",
                         inventory.root / "doesnotexist",
                         dir_path])


@pytest.mark.ui({'yes': True})
def test_onyo_tree_single(inventory: Inventory) -> None:
    """Display a tree for a directory."""
    directory_path = inventory.root / "somewhere" / "nested"

    # move an asset and a dir to the same destination
    onyo_tree(inventory,
              paths=[directory_path])

    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_multiple_paths(inventory: Inventory) -> None:
    """Display multiple trees with one call."""
    dir_path = inventory.root / 'somewhere' / 'nested'

    onyo_tree(inventory,
              paths=[dir_path,
                     inventory.root])

    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_without_explicit_paths(inventory: Inventory) -> None:
    """Display the root of the inventory, if onyo_tree() is called without paths."""
    onyo_tree(inventory)

    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_errors_before_showing_trees(inventory: Inventory) -> None:
    """`onyo_tree` must raise the correct error if one of the paths does not exist."""
    directory_path = inventory.root / "somewhere" / "nested"
    non_existing_path = inventory.root / "doesnotexist"

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[directory_path,
                         non_existing_path,
                         inventory.root])

    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.repo_dirs("a/b/c", "a/d/c")
def test_onyo_tree_with_same_dir_twice(inventory: Inventory) -> None:
    """Allow to display the tree to a directory twice when `onyo_tree()` is called with the same
    path twice at once."""
    directory_path = inventory.root / "somewhere" / "nested"

    # call onyo_tree() with `directory_path` twice in `paths`.
    onyo_tree(inventory,
              paths=[directory_path,
                     inventory.root,
                     directory_path])

    # TODO: verifying cleanness of worktree does not work,
    #       because fixture returns inventory with untracked stuff
    # assert inventory.repo.git.is_clean_worktree()
