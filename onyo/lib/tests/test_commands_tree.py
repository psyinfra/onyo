import pytest

from onyo.lib.inventory import Inventory
from ..commands import onyo_tree

# TODO: test output?


@pytest.mark.ui({'yes': True})
def test_onyo_tree_errors(inventory: Inventory) -> None:
    r"""`onyo_tree` must raise the correct error in different illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'

    # no tree for files
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[(str(asset_path), asset_path)])

    # non-existing dir
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[(str(dir_path / "doesnotexist"), dir_path / "doesnotexist")])

    # existing dir, but outside of onyo repository
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[(str(inventory.root / ".."), inventory.root / "..")])

    # one of many paths invalid
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[(str(inventory.root / "somewhere" / "nested"), inventory.root / "somewhere" / "nested"),
                         (str(inventory.root / "doesnotexist"), inventory.root / "doesnotexist"),
                         (str(dir_path), dir_path)])

    # no error scenario leaves the git worktree unclean
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_single(inventory: Inventory,
                          capsys) -> None:
    r"""Display a tree for a directory."""
    directory_path = inventory.root / "somewhere" / "nested"

    # move an asset and a dir to the same destination
    onyo_tree(inventory,
              paths=[(str(directory_path), directory_path)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(include=[directory_path]):
        assert all([part in tree_output for part in path.parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_dirs_only(inventory: Inventory,
                             capsys) -> None:
    r"""Display a tree w/o any files"""
    inventory.add_asset(dict(type="atype",
                             make="someone",
                             model=dict(name="fancy"),
                             serial="faux",
                             directory=inventory.root,
                             is_asset_directory=True))
    inventory.commit("Add an asset dir to make sure it's not excluded.")
    onyo_tree(inventory,
              paths=[(str(inventory.root), inventory.root)],
              dirs_only=True)
    tree_output = capsys.readouterr().out
    for path in inventory.root.rglob('*'):
        if not path.is_dir() or any(p.startswith('.') for p in path.parts):
            # If it's not a dir it shouldn't be displayed.
            # Note: Any part of a file path including the file's name
            # may show up somewhere in the output as a dir.
            # In the test case, however, this is only applying to `.onyo/templates/empty`
            # and `empty/`. Hence, should be protected against b/c of the leading dot.
            assert not all([part in tree_output for part in path.parts])
        else:
            assert all([part in tree_output for part in path.parts])


@pytest.mark.ui({'yes': True})
def test_onyo_tree_multiple_paths(inventory: Inventory,
                                  capsys) -> None:
    r"""Display multiple trees with one call."""
    dir_path = inventory.root / 'somewhere' / 'nested'

    onyo_tree(inventory,
              paths=[(str(dir_path), dir_path),
                     (str(inventory.root), inventory.root)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(include=[dir_path, inventory.root]):
        assert all([part in tree_output for part in path.parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_relative_single(inventory: Inventory,
                                   capsys) -> None:
    r"""Display a tree for a relative subdirectory."""
    directory_path = inventory.root / "somewhere" / "nested"

    # move an asset and a dir to the same destination
    onyo_tree(inventory,
              paths=[("somewhere/nested", directory_path)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(include=[directory_path]):
        assert all([part in tree_output for part in path.relative_to(inventory.root).parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
def test_onyo_tree_errors_before_showing_trees(inventory: Inventory) -> None:
    r"""`onyo_tree` must raise the correct error if one of the paths does not exist."""
    directory_path = inventory.root / "somewhere" / "nested"
    non_existing_path = inventory.root / "doesnotexist"

    # one of multiple paths does not exist
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  paths=[(str(directory_path), directory_path),
                         (str(non_existing_path), non_existing_path),
                         (str(inventory.root), inventory.root)])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.ui({'yes': True})
@pytest.mark.repo_dirs("a/b/c", "a/d/c")
def test_onyo_tree_with_same_dir_twice(inventory: Inventory,
                                       capsys) -> None:
    r"""Allow to display the tree to a directory twice when
    `onyo_tree()` is called with the same path twice at once."""
    directory_path = inventory.root / "somewhere" / "nested"

    # call onyo_tree() with `directory_path` twice in `paths`.
    onyo_tree(inventory,
              paths=[(str(directory_path), directory_path),
                     (str(inventory.root), inventory.root),
                     (str(directory_path), directory_path)])

    # verify assets and paths are in output
    tree_output = capsys.readouterr().out
    for path in inventory.repo.get_asset_paths(include=[directory_path]):
        assert all([part in tree_output for part in path.parts])
    assert tree_output.count(str(directory_path)) == 2
    assert inventory.repo.git.is_clean_worktree()
