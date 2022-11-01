import subprocess
from pathlib import Path
import pytest


# NOTE: the output of `onyo history` is not tested for formatting or content, as
#       the commands called by `onyo history` are user-configurable. Instead, it
#       is tested for whether the output of the underlying command is unaltered.
variants = [
    'file',
    'dir',
    'dir/subfile-1',
    's p a c e s/subfile-2',
    's p a/c e s/sub file 3',
]
@pytest.mark.repo_files('file', 'dir/subfile-1', 's p a c e s/subfile-2', 's p a/c e s/sub file 3')
@pytest.mark.parametrize('variant', variants)
def test_history_noninteractive(repo, variant):
    ret = subprocess.run(['onyo', 'history', '-I', variant],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


variants = [
    'does-not-exist',
    'subdir/does-not-exist',
]
@pytest.mark.repo_dirs('subdir')
@pytest.mark.parametrize('variant', variants)
def test_history_noninteractive_not_exist(repo, variant):
    ret = subprocess.run(['onyo', 'history', '-I', variant],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


variants = {  # pyre-ignore[9]
    'both-exist': ['file', 'dir/subfile-1'],
    'first-exist': ['file', 'does-not-exist'],
    'second-exist': ['does-not-exist', 'file'],
}
@pytest.mark.repo_files('file', 'dir/subfile-1')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_history_noninteractive_too_many_args(repo, variant):
    ret = subprocess.run(['onyo', 'history', '-I'] + variant,
                         capture_output=True, text=True)
    assert ret.returncode != 0
    assert not ret.stdout
    assert ret.stderr


# NOTE: interactive cannot be tested directly, as onyo detects whether it's
#       connected to a TTY.
@pytest.mark.repo_files('file')
def test_history_interactive_fallback(repo):
    ret = subprocess.run(['onyo', 'history', 'file'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


# Error when no config flag is found
@pytest.mark.repo_files('file')
def test_history_config_unset(repo):
    """
    The command should error when no tool is configured.
    """
    # unset config for history tool
    ret = subprocess.run(['onyo', 'config', '--unset', 'onyo.history.non-interactive'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not repo.get_config('onyo.history.non-interactive')

    # test
    ret = subprocess.run(['onyo', 'history', '-I', 'file'],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_files('file')
def test_history_config_invalid(repo):
    # set to invalid
    repo.set_config('onyo.history.non-interactive', 'does-not-exist-in-path')

    # run history
    ret = subprocess.run(['onyo', 'history', '-I', 'file'],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "'does-not-exist-in-path' was not found" in ret.stderr


# Reconfigure the history command to tickle some other functionality we're
# interested in.
variants = [
    'file',
    'dir/subfile-1',
    's p a/c e s/sub file 3',
]
@pytest.mark.repo_files('file', 'dir/subfile-1', 's p a c e s/subfile-2', 's p a/c e s/sub file 3')
@pytest.mark.parametrize('variant', variants)
def test_history_fake_noninteractive_stdout(repo, variant):
    repo.set_config('onyo.history.non-interactive', '/usr/bin/env printf')

    # test
    ret = subprocess.run(['onyo', 'history', '-I', variant],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert Path(ret.stdout).resolve() == Path(variant).resolve()
    assert not ret.stderr


variants = [
    'file',
    'dir/subfile-1',
    's p a/c e s/sub file 3',
]
@pytest.mark.repo_files('file', 'dir/subfile-1', 's p a c e s/subfile-2', 's p a/c e s/sub file 3')
@pytest.mark.parametrize('variant', variants)
def test_history_fake_noninteractive_stderr(repo, variant):
    repo.set_config('onyo.history.non-interactive', '/usr/bin/env printf >&2')

    # test
    ret = subprocess.run(['onyo', 'history', '-I', variant],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert Path(ret.stderr).resolve() == Path(variant).resolve()


variants = {  # pyre-ignore[9]
    'success': {
        'cmd': '/usr/bin/env true',
        'retval': 0,
    },
    'error': {
        'cmd': '/usr/bin/env false',
        'retval': 1,
    },
    'error-129': {
        'cmd': 'git config --invalid-flag-oopsies',
        'retval': 129,
    },
}
@pytest.mark.repo_files('file')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_history_fake_noninteractive_bubble_exit_code(repo, variant):
    repo.set_config('onyo.history.non-interactive', variant['cmd'])

    ret = subprocess.run(['onyo', 'history', '-I', 'file'],
                         capture_output=True, text=True)
    assert ret.returncode == variant['retval']
