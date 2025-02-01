from __future__ import annotations

import pytest
from pathlib import Path

from onyo.lib.command_utils import (
    inline_path_diff,
)

@pytest.mark.parametrize("source, destination",
                         [("Bingo Bob", "/one/two/Banjo Jim"),
                          (Path("/one/two/Bingo Bob"), "Banjo Jim"),
                          (Path("/Bingo Bob"), Path("Banjo Jim")),
                         ])
def test_inline_path_diff_error(source, destination) -> None:
    r"""Test the errors of inline_path_diff()."""
    with pytest.raises(ValueError):
        inline_path_diff(source, destination)


def test_inline_path_diff() -> None:
    r"""Test the output of inline_path_diff()."""

    #
    # Types
    #
    # string
    result = inline_path_diff("Bingo Bob", "one/two/Bingo Bob")
    assert result == "Bingo Bob -> one/two/Bingo Bob"

    # Path
    result = inline_path_diff(Path("Bingo Bob"), Path("one/two/Bingo Bob"))
    assert result == "Bingo Bob -> one/two/Bingo Bob"

    # Path and string (become some people can't make up their minds)
    result = inline_path_diff(Path("Bingo Bob"), "one/two/Bingo Bob")
    assert result == "Bingo Bob -> one/two/Bingo Bob"


    #
    # Top-level operations use no "{}" to group
    #
    # move without rename
    result = inline_path_diff("Bingo Bob", "one/two/Bingo Bob")
    assert result == "Bingo Bob -> one/two/Bingo Bob"

    result = inline_path_diff("one/two/Bingo Bob", "Bingo Bob")
    assert result == "one/two/Bingo Bob -> Bingo Bob"

    # move with rename
    result = inline_path_diff("Bingo Bob", "one/two/Banjo Jim")
    assert result == "Bingo Bob -> one/two/Banjo Jim"

    result = inline_path_diff("one/two/Bingo Bob", "Banjo Jim")
    assert result == "one/two/Bingo Bob -> Banjo Jim"


    #
    # Single Groups
    #
    # rename
    result = inline_path_diff("one/two/Bingo Bob", "one/two/Banjo Jim")
    assert result == "one/two/{Bingo Bob -> Banjo Jim}"

    ### right edge single group

    # move lateral
    result = inline_path_diff("one/two/Bingo Bob", "one/alpha/Bingo Bob")
    assert result == "one/{two -> alpha}/Bingo Bob"

    # move down
    result = inline_path_diff("one/two/Bingo Bob", "one/two/three/Bingo Bob")
    assert result == "one/{two -> two/three}/Bingo Bob"

    # move up
    result = inline_path_diff("one/two/three/Bingo Bob", "one/two/Bingo Bob")
    assert result == "one/{two/three -> two}/Bingo Bob"

    ### left edge single group

    # move lateral
    result = inline_path_diff("one/two/Bingo Bob", "alpha/two/Bingo Bob")
    assert result == "{one -> alpha}/two/Bingo Bob"

    # move down
    result = inline_path_diff("one/two/Bingo Bob", "alpha/one/two/Bingo Bob")
    assert result == "{one -> alpha/one}/two/Bingo Bob"

    # move up
    result = inline_path_diff("one/two/three/Bingo Bob", "two/three/Bingo Bob")
    assert result == "{one/two -> two}/three/Bingo Bob"

    ### middle single group

    # move lateral
    result = inline_path_diff("one/two/three/Bingo Bob", "one/alpha/three/Bingo Bob")
    assert result == "one/{two -> alpha}/three/Bingo Bob"

    # move down
    result = inline_path_diff("one/two/three/Bingo Bob", "one/alpha/two/three/Bingo Bob")
    assert result == "one/{two -> alpha/two}/three/Bingo Bob"

    # move down
    result = inline_path_diff("one/two/three/Bingo Bob", "one/two/alpha/three/Bingo Bob")
    assert result == "one/two/{three -> alpha/three}/Bingo Bob"

    # move up
    result = inline_path_diff("one/two/three/four/Bingo Bob", "one/three/four/Bingo Bob")
    assert result == "one/{two/three -> three}/four/Bingo Bob"

    # move up
    result = inline_path_diff("one/two/three/four/Bingo Bob", "one/two/three/Bingo Bob")
    assert result == "one/two/{three/four -> three}/Bingo Bob"


    #
    # Multiple Groups
    #
    # move lateral
    result = inline_path_diff("one/two/three/four/five/Bingo Bob", "alpha/two/beta/four/gamma/Bingo Bob")
    assert result == "{one -> alpha}/two/{three -> beta}/four/{five -> gamma}/Bingo Bob"

    # move lateral
    result = inline_path_diff("one/two/three/four/five/Bingo Bob", "one/alpha/three/beta/five/Bingo Bob")
    assert result == "one/{two -> alpha}/three/{four -> beta}/five/Bingo Bob"

    # move down
    # note: there is no "right" answer here. This grouping is an artifact of the algorithm,
    result = inline_path_diff("one/two/three/Bingo Bob", "one/alpha/two/beta/three/gamma/Bingo Bob")
    assert result == "one/{two -> alpha/two/beta}/{three -> three/gamma}/Bingo Bob"

    # move down
    # note: there is no "right" answer here. This grouping is an artifact of the algorithm,
    result = inline_path_diff("one/two/three/Bingo Bob", "alpha/one/beta/two/gamma/three/Bingo Bob")
    assert result == "{one -> alpha/one/beta}/two/{three -> gamma/three}/Bingo Bob"

    # move up
    # note: there is no "right" answer here. This grouping is an artifact of the algorithm,
    result = inline_path_diff("one/alpha/two/beta/three/gamma/Bingo Bob", "one/two/three/Bingo Bob")
    assert result == "one/{alpha/two/beta -> two}/{three/gamma -> three}/Bingo Bob"

    # move up
    # note: there is no "right" answer here. This grouping is an artifact of the algorithm,
    result = inline_path_diff("alpha/one/beta/two/gamma/three/Bingo Bob", "one/two/three/Bingo Bob")
    assert result == "{alpha/one/beta -> one}/two/{gamma/three -> three}/Bingo Bob"


    #
    # Complex / Weird
    #
    # everything changes
    result = inline_path_diff("one/two/three/Bingo Bob", "alpha/beta/gamma/Banjo Jim")
    assert result == "{one/two/three -> alpha/beta/gamma}/{Bingo Bob -> Banjo Jim}"

    # nothing changes
    result = inline_path_diff("one/two/three/Bingo Bob", "one/two/three/Bingo Bob")
    assert result == "one/two/three/Bingo Bob"

    # two multi-length groupings move down
    result = inline_path_diff("one/two/three/four/Bingo Bob", "one/alpha/beta/three/gamma/delta/Bingo Bob")
    assert result == "one/{two -> alpha/beta}/three/{four -> gamma/delta}/Bingo Bob"

    # two multi-length groupings move up
    result = inline_path_diff("one/alpha/beta/three/gamma/delta/Bingo Bob", "one/two/three/four/Bingo Bob")
    assert result == "one/{alpha/beta -> two}/three/{gamma/delta -> four}/Bingo Bob"

    # invert
    result = inline_path_diff("one/two/three/four/five/Bingo Bob", "five/four/three/two/one/Bingo Bob")
    # note: there is no "right" answer here. This grouping is an artifact of the algorithm,
    assert result == "{one -> five/four/three}/two/{three/four/five -> one}/Bingo Bob"

    # repeats
    result = inline_path_diff("a/a/a/h/Bingo Bob", "a/a/a/h/h/Bingo Bob")
    assert result == "a/a/a/{h -> h/h}/Bingo Bob"

    # repeat pyramid
    result = inline_path_diff("a/a/a/h/h/h/a/a/a/Bingo Bob", "a/a/h/h/a/a/Bingo Bob")
    # note: there is no "right" answer here. This grouping is an artifact of the algorithm,
    assert result == "a/a/{a -> h}/h/{h/h -> a}/{a/a/a -> a}/Bingo Bob"
