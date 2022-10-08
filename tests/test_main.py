from itertools import product

from onyo import main


def test_get_subcmd_index_missing(helpers):
    """
    Test all possible combinations of flags for onyo, without any subcommand.
    """
    for i in helpers.powerset(helpers.onyo_flags()):
        for k in product(*i):
            args = list(helpers.flatten(k))
            full_cmd = ['onyo'] + args
            idx = main.get_subcmd_index(full_cmd)
            assert idx is None


def test_get_subcmd_index_valid(helpers):
    """
    Test all possible combinations of flags for onyo, with a subcommand.
    """
    for i in helpers.powerset(helpers.onyo_flags()):
        for k in product(*i):
            args = list(helpers.flatten(k))
            full_cmd = ['onyo'] + args + ['config', '--get', 'onyo.core.editor']
            idx = main.get_subcmd_index(full_cmd)
            assert idx is full_cmd.index('config')
