import random
import pytest
import subprocess

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


variants = ['laptop_apple_macbookpro_0',
            'lap top _ app le _ mac book pro_ 0']
@pytest.mark.parametrize('variant', variants)
def test_error_invalid_namescheme_no_dot(repo: Repo, variant: str) -> None:
    """
    Test that `onyo new` prints correct errors for different invalid names if
    the '.' is missing in the asset name.
    """
    ret = subprocess.run(['onyo', 'new', variant], capture_output=True, text=True)
    assert not ret.stdout
    assert ret.returncode == 1
    assert "Asset names must have a '.'" in ret.stderr

    # verify that no new assets were created and the repository state is clean
    assert len(repo.assets) == 0
    repo.fsck()


variants = ['laptop_ap.ple_macbookpro.0',
            'lap_top_apple_macbookpro.0',
            'laptop-apple-macbookpro.0']
@pytest.mark.parametrize('variant', variants)
def test_error_invalid_namescheme_wrong_format(repo: Repo, variant: str) -> None:
    """
    Test that `onyo new` prints correct errors for different invalid names:
    - '.' in another field as serial number
    - Additional '_' in one of the early fields
    - instead of '_' using '-' to divide fields
    """
    ret = subprocess.run(['onyo', 'new', variant], capture_output=True, text=True)
    assert not ret.stdout
    assert ret.returncode == 1
    assert "must be in the format '<type>_<make>_<model>.<serial>'" in ret.stderr

    # verify that no new assets were created and the repository state is clean
    assert len(repo.assets) == 0
    repo.fsck()


variants = ['_apple_macbookpro.0',
            'laptop__macbookpro.0',
            'laptop_apple_.0',
            'laptop_apple_macbookpro.'
            ]
@pytest.mark.parametrize('variant', variants)
def test_error_invalid_namescheme_empty_fields(repo: Repo, variant: str) -> None:
    """
    Test the correct error if a name field ('type', 'make', 'model', 'serial')
    is empty, while the format (e.g. needed '_' and '.' exist) is correct.
    """
    ret = subprocess.run(['onyo', 'new', variant], capture_output=True, text=True)
    assert not ret.stdout
    assert ret.returncode == 1
    assert "The fields 'type', 'make', 'model' and 'serial' are not allowed to be empty." in ret.stderr

    # verify that no new assets were created and the repository state is clean
    assert len(repo.assets) == 0
    repo.fsck()
