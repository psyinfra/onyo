import pytest

from onyo.lib.inventory import Inventory
from ..commands import onyo_tree


def test_onyo_tree_errors(inventory: Inventory,
                          capsys) -> None:
    r"""Raise the correct error for illegal or impossible calls."""
    asset_path = inventory.root / "somewhere" / "nested" / "TYPE_MAKER_MODEL.SERIAL"
    dir_path = inventory.root / 'empty'

    # no tree for files
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  path=asset_path)

    # non-existing dir
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  path=dir_path / "doesnotexist")

    # existing dir, but outside of onyo repository
    pytest.raises(ValueError,
                  onyo_tree,
                  inventory,
                  path=inventory.root / "..")

    # nothing should be printed when the path is invalid
    assert capsys.readouterr().out == ''

    # no error scenario leaves the git worktree unclean
    assert inventory.repo.git.is_clean_worktree()


def test_onyo_tree(inventory: Inventory,
                   capsys) -> None:
    r"""Display a tree for a directory."""
    directory_path = inventory.root / "somewhere" / "nested"

    onyo_tree(inventory,
              path=directory_path)

    tree_output = capsys.readouterr().out
    # root node is path
    assert tree_output.startswith(f"{directory_path}\n")
    # assets and paths are in output
    for path in inventory.repo.get_asset_paths(include=[directory_path]):
        assert all([part in tree_output for part in path.parts])
    assert inventory.repo.git.is_clean_worktree()


@pytest.mark.parametrize('desc', ['/absolute/path',
                                  'relative/path',
                                  '.',
                                  'arbitrary string',
                                  ''])
def test_onyo_tree_description(inventory: Inventory,
                               desc: str,
                               capsys) -> None:
    r"""The description should be used and unaltered."""
    directory_path = inventory.root / "somewhere" / "nested"

    onyo_tree(inventory,
              path=directory_path,
              description=desc)

    # that the description is printed verbatim as the root node
    assert capsys.readouterr().out.startswith(f"{desc}\n")

    assert inventory.repo.git.is_clean_worktree()


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
              path=inventory.root,
              dirs_only=True)

    tree_output = capsys.readouterr().out
    # root node is path
    assert tree_output.startswith(f"{inventory.root}\n")
    # check tree
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
