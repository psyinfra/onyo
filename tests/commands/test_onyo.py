import subprocess
from itertools import product

import pytest


variants = [
    '-d',
    '--debug',
]
@pytest.mark.repo_dirs('just-a-dir')
@pytest.mark.parametrize('variant', variants)
def test_onyo_debug(repo, variant):
    ret = subprocess.run(['onyo', variant, 'mkdir', '--yes', f'flag{variant}'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert 'DEBUG:onyo' in ret.stderr


variants = [
    '-h',
    '--help',
]
@pytest.mark.parametrize('variant', variants)
def test_onyo_help(repo, variant):
    ret = subprocess.run(['onyo', variant], capture_output=True, text=True)
    assert ret.returncode == 0
    assert 'usage: onyo [-h]' in ret.stdout
    assert not ret.stderr


# TODO: this would be better if parametrized
def test_onyo_without_subcommand(repo, helpers):
    """
    Test all possible combinations of flags for onyo, without any subcommand.
    """
    for i in helpers.powerset(helpers.onyo_flags()):
        for k in product(*i):
            args = list(helpers.flatten(k))
            full_cmd = ['onyo'] + args

            ret = subprocess.run(full_cmd, capture_output=True, text=True)
            assert ret.returncode == 1
            assert 'usage: onyo [-h]' in ret.stdout
            assert not ret.stderr
