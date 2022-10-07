import subprocess
from itertools import product


def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0


def test_onyo_debug(helpers):
    # populate repo, so there's something to be noisy about
    ret = subprocess.run(['onyo', 'mkdir', 'just-a-dir'])
    assert ret.returncode == 0

    for i in ['-d', '--debug']:
        full_cmd = ['onyo', i, 'mkdir', f'flag{i}']

        ret = subprocess.run(full_cmd, capture_output=True, text=True)
        assert ret.returncode == 0
        assert 'DEBUG:onyo' in ret.stderr


def test_onyo_help(helpers):
    for i in ['-h', '--help']:
        full_cmd = ['onyo', i]

        ret = subprocess.run(full_cmd, capture_output=True, text=True)
        assert ret.returncode == 0
        assert 'usage: onyo [-h]' in ret.stdout
        assert not ret.stderr


def test_onyo_without_subcommand(helpers):
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
