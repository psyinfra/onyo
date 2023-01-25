import random
import pytest

from onyo.lib import Repo

# generate 50 random pairings of length and num.
variants = {f'{length} x {num}': (length, num) for length in random.sample(range(4, 20), 10) for num in random.sample(range(1, 10000), 5)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials(repo, variant):
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
variants = {f'{length} x {num}': (length, num) for length in range(-2, 4) for num in random.sample(range(1, 10000), 5)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials_invalid_length(repo, variant):
    """
    Fewer than 4 character in the serial is invalid.
    """
    # faux serial numbers must have at least length 1 and the function raises
    # ValueError:
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)


# generate 15 invalid random pairings of length and num.
variants = {f'{length} x {num}': (length, num) for length in random.sample(range(4, 20), 5) for num in range(-2, 1)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials_invalid_number(repo, variant):
    """
    Number of serials must be greater than 0.
    """
    # faux serial numbers must have at least length 1 and the function raises
    # ValueError:
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)


# generate mutually invalid pairings of length and num.
variants = {f'{length} x {num}': (length, num) for length in range(0, 4) for num in range(-2, 1)}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_generate_faux_serials_invalid_length_and_number(repo, variant):
    """
    Both length and number are invalid.
    """
    # faux serial numbers must have at least length 1 and the function raises
    # ValueError:
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)
