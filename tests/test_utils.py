import subprocess
from pathlib import Path

import pytest
from onyo import utils


def test_get_config_value_git(repo):
    ret = subprocess.run(["git", "config", "onyo.test.get-git", "get-git-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert 'get-git =' in Path('.git/config').read_text()
    assert '= get-git-test' in Path('.git/config').read_text()

    assert utils.get_config_value('onyo.test.get-git', repo.root) == 'get-git-test'


def test_get_config_value_onyo(repo):
    ret = subprocess.run(["onyo", "config", "onyo.test.get-onyo", "get-onyo-test"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert 'get-onyo =' in Path('.onyo/config').read_text()
    assert '= get-onyo-test' in Path('.onyo/config').read_text()

    assert utils.get_config_value('onyo.test.get-onyo', repo.root) == 'get-onyo-test'


def test_generate_faux_serials(repo):
    """
    Test the creation of unique serial numbers with the default length through
    calling the generate_faux_serial() function multiple times and comparing the
    generated faux serial numbers.
    """
    # creating multiple faux serial numbers without actually creating assets
    # might lead to duplicates. In practice, this should not happen if they are
    # sufficiently long and random
    faux = [utils.generate_faux_serial(repo.root) for x in range(0, 100)]
    assert len(faux) == len(set(faux))
    assert len(faux) > 0


def test_length_range_of_generate_faux_serials(repo):
    """
    Create many faux serial numbers with different lengths over the range of
    allowed faux serial number lengths to test that the function returns faux
    serial numbers, as well as for the values 0 and 38 outside of the interval
    to verify that the appropriate error gets thrown. Because of the
    different lengths, they should all be different.
    """
    # faux serial numbers must have at least length 1 and the function raises
    # ValueError:
    with pytest.raises(ValueError) as ret:
        utils.generate_faux_serial(repo.root, faux_length=0)
    assert ret.type == ValueError

    # faux serial numbers can't be requested longer than 37 and the function
    # raises ValueError:
    with pytest.raises(ValueError) as ret:
        utils.generate_faux_serial(repo.root, faux_length=38)
    assert ret.type == ValueError

    faux = [utils.generate_faux_serial(repo.root, x) for x in range(1, 37)]
    assert len(faux) == len(set(faux))
    assert len(faux) > 0
