from pathlib import Path

import pytest


# NOTE: configuration options can be set in multiple locations:
# - system (/etc/gitconfig)
# - global (~/.gitconfig)
# - local (.git/config)
# - worktree (.git/config or .git/config.worktree if extensions.worktreeConfig is present)
# - onyo (.onyo/config)
#
# 'system` and 'global' are left untested, to not tamper with developer machines.

variants = {
    'default': {
        'args': ('onyo.test.set-config', 'default'),
        'file': '.onyo/config',
    },
    'local': {
        'args': ('onyo.test.set-config', 'local', 'local'),
        'file': '.git/config',
    },
    'worktree': {
        'args': ('onyo.test.set-config', 'worktree', 'worktree'),
        'file': '.git/config.worktree'
    },
    'onyo': {
        'args': ('onyo.test.set-config', 'onyo', 'onyo'),
        'file': '.onyo/config',
    },
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_set_config(repo, variant):
    """
    Set config in different locations.

    NOTE: 'global' and 'system' are untested to not touch the user or system config.
    """
    # set extensions.worktreeConfig (for the 'worktree' test)
    repo._git(['config', 'extensions.worktreeConfig', 'true'])

    # test
    repo.set_config(*variant['args'])
    value = variant['args'][1]
    assert f'set-config = {value}' in Path(repo.root, variant['file']).read_text()


def test_set_config_invalid_location(repo):
    """
    Invalid location should throw an exception.
    """
    with pytest.raises(ValueError):
        repo.set_config('onyo.test.set-config-invalid-location', 'valid-value', location='completely-invalid')


variants = {  # pyre-ignore[9]
    'wlo-worktree': {
        'set': ['worktree', 'local', 'onyo'],
        'answer': 'worktree',
    },
    'wl-worktree': {
        'set': ['worktree', 'local'],
        'answer': 'worktree',
    },
    'wo-worktree': {
        'set': ['worktree', 'onyo'],
        'answer': 'worktree',
    },
    'lo-local': {
        'set': ['local', 'onyo'],
        'answer': 'local',
    },
    'solo-worktree': {
        'set': ['worktree'],
        'answer': 'worktree',
    },
    'solo-local': {
        'set': ['local'],
        'answer': 'local',
    },
    'solo-onyo': {
        'set': ['onyo'],
        'answer': 'onyo',
    },
}
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_get_config_precedence(repo, variant):
    """
    The order of precedence is worktree > local > global > system > onyo.

    NOTE: 'global' and 'system' are untested to not touch the user or system config.
    """
    # enable worktreeConfig, so it doesn't save over "local"
    repo._git(['config', 'extensions.worktreeConfig', 'true'])

    # set locations
    for i in variant['set']:
        repo.set_config('onyo.test.get-config-precedence', i, location=i)

    # test
    ret = repo.get_config('onyo.test.get-config-precedence')
    assert ret == variant['answer']


def test_get_config_name_not_exist(repo):
    """
    Missing values should return None
    """
    ret = repo.get_config('onyo.test.get-config-name-does-not-exist')
    assert ret is None


def test_get_config_empty_value(repo):
    """

    """
    repo.set_config('onyo.test.get-config-empty-value', '')

    # test
    ret = repo.get_config('onyo.test.get-config-empty-value')
    assert ret == ''
