import random
import pytest
from pathlib import Path

from onyo.lib import Repo
from typing import Dict, Tuple, List

# generate 50 random pairings of length and num.
variants: Dict[str, Tuple[int, int]] = {f'{length} x {num}': (length, num) for length in random.sample(range(4, 20), 10) for num in random.sample(range(1, 10000), 5)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials(repo: Repo, variant: List[int]) -> None:
    """
    Generate a faux serial numbers of variable length and quantity.
    """
    length = variant[0]
    num = variant[1]

    serials = repo.generate_faux_serials(*variant)
    assert isinstance(serials, set)
    assert len(serials) == num

    for i in serials:
        assert isinstance(i, str)
        assert 'faux' in i
        assert len(i) == length + len('faux')


# generate 30 invalid random pairings of length and num.
variants: Dict[str, Tuple[int, int]] = {f'{length} x {num}': (length, num) for length in range(-2, 4) for num in random.sample(range(1, 10000), 5)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials_invalid_length(repo: Repo,
                                              variant: List[int]) -> None:
    """
    Fewer than 4 character in the serial is invalid.
    """
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)


# generate 15 invalid random pairings of length and num.
variants: Dict[str, Tuple[int, int]] = {f'{length} x {num}': (length, num) for length in random.sample(range(4, 20), 5) for num in range(-2, 1)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials_invalid_number(repo: Repo,
                                              variant: List[int]) -> None:
    """
    Number of serials must be greater than 0.
    """
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)


# generate mutually invalid pairings of length and num.
variants: Dict[str, Tuple[int, int]] = {f'{length} x {num}': (length, num) for length in range(0, 4) for num in range(-2, 1)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials_invalid_length_and_number(
        repo: Repo, variant: List[int]) -> None:
    """
    Both length and number are invalid.
    """
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)


@pytest.mark.parametrize('variant', [
    'laptop_apple_macbookpro_0',  # no .
    'laptop-apple-macbookpro.0',  # no _
    'laptop-apple-macbookpro-0',  # no _ or -
    'laptop_ap.ple_macbookpro.0',  # . can only be in serial field
    'lap_top_apple_macbookpro.0',  # too many fields (_)
    '__.',  # all fields are empty
    '_apple_macbookpro.0',  # empty type
    'laptop__macbookpro.0',  # empty make
    'laptop_apple_.0',  # empty model
    'laptop_apple_macbookpro.'  # empty serial
])
def test_valid_name_error(repo: Repo, variant: str) -> None:
    """
    Test `Repo.valid_name()` against invalid asset names.
    """
    for asset in [variant, Path(variant)]:
        valid = repo.valid_name(asset)
        assert isinstance(valid, bool)
        assert not valid


@pytest.mark.parametrize('variant', [
    'laptop_apple_macbookpro.serial123',  # normal
    'lap top_app le_mac book.ser ial',  # spaces are allowed
    'laptop_apple_macbookpro.serial_a.b_c.d'  # serial allows any characters
])
def test_valid_name(repo: Repo, variant: str) -> None:
    """
    Test `Repo.valid_name()` against valid asset names --- including weird ones.
    """
    for asset in [variant, Path(variant)]:
        valid = repo.valid_name(asset)
        assert isinstance(valid, bool)
        assert valid
