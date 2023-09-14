import subprocess
from itertools import product

from onyo.lib import OnyoRepo
from onyo.lib.commands import fsck
import pytest


@pytest.mark.repo_dirs('just-a-dir')
@pytest.mark.parametrize('variant', ['-d', '--debug'])
def test_onyo_debug(repo: OnyoRepo, variant: str) -> None:
    ret = subprocess.run(['onyo', variant, '--yes', 'mkdir', f'flag{variant}'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert 'DEBUG:onyo' in ret.stderr
    fsck(repo)


@pytest.mark.parametrize('variant', ['-h', '--help'])
def test_onyo_help(repo: OnyoRepo, variant: str) -> None:
    ret = subprocess.run(['onyo', variant], capture_output=True, text=True)
    assert ret.returncode == 0
    assert 'usage: onyo [-h]' in ret.stdout
    assert not ret.stderr
    fsck(repo)


# TODO: this would be better if parametrized
def test_onyo_without_subcommand(repo: OnyoRepo, helpers) -> None:
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
    fsck(repo)
