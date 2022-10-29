import random
import pytest


# generate 50 random pairings of length and num.
variants = {(length, num) for length in random.sample(range(4, 20), 10) for num in random.sample(range(1, 10000), 5)}
@pytest.mark.parametrize('variant', variants)
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


# generate 20 invalid random pairings of length and num.
variants = {(length, num) for length in range(0, 3) for num in random.sample(range(1, 10000), 5)}
@pytest.mark.parametrize('variant', variants)
def test_length_range_of_generate_faux_serials(repo, variant):
    """
    Fewer than 4 character in the serial is invalid.
    """
    # faux serial numbers must have at least length 1 and the function raises
    # ValueError:
    with pytest.raises(ValueError):
        repo.generate_faux_serials(*variant)
