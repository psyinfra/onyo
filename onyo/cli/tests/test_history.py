import subprocess
from pathlib import Path
from typing import List

import pytest

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import fsck

# NOTE: the output of `onyo history` is not tested for formatting or content, as
#       the commands called by `onyo history` are user-configurable. Instead, it
#       is tested for whether the output of the underlying command is unaltered.


files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro',
         'spe\"c_ialch_ar\'ac.teஞrs']

directories = ['.',
               's p a c e s',
               'very/very/very/deep',
               ]

assets: List[str] = [f"{d}/{f}.{i}" for f in files for i, d in enumerate(directories)]


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_history_noninteractive(repo: OnyoRepo, asset: str) -> None:
    """
    Test that the default `onyo history -I ASSET` command runs and print to
    std.out, but not std.err.
    """
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    fsck(repo)


@pytest.mark.repo_dirs(*assets)
@pytest.mark.parametrize('asset', ['does_not_exist.test',
                                   'subdir/does_not_exist.test'])
def test_history_noninteractive_not_exist(repo: OnyoRepo, asset: str) -> None:
    """
    Test that `onyo history -I ASSET` when called on non-existing assets does
    correctly print into ret.stderr.
    """
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    fsck(repo)


@pytest.mark.repo_files('file_does_exist.test', 'dir/file_in_subdir.test')
@pytest.mark.parametrize('variant',
                         [['file_does_exist.test', 'dir/file_in_subdir.test'],
                          ['file_does_exist.test', 'does_not_exist.test'],
                          ['does_not_exist.test', 'file_does_exist.test']]
                         )
def test_history_noninteractive_too_many_args(repo: OnyoRepo, variant: list[str]) -> None:
    """
    Test that `onyo history -I` does not allow multiple input arguments.
    """
    ret = subprocess.run(['onyo', 'history', '-I', *variant],
                         capture_output=True, text=True)
    assert ret.returncode != 0
    assert not ret.stdout
    assert ret.stderr
    fsck(repo)


@pytest.mark.repo_files(assets[0])
def test_history_interactive_fallback(repo: OnyoRepo) -> None:
    """
    Test `onyo history` does work without the `-I` flag.

    Note that the interactive mode cannot be tested directly, as onyo detects
    whether it's connected to a TTY.
    """
    ret = subprocess.run(['onyo', 'history', assets[0]],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    fsck(repo)


@pytest.mark.repo_files(assets[0])
def test_history_config_unset(repo: OnyoRepo) -> None:
    """
    Test that `onyo history` errors when no tool is configured.
    """
    # unset config for history tool
    repo.set_config('onyo.history.non-interactive', '')
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Unset in .onyo/config: 'onyo.history.non-interactive'")

    # verify unset
    assert not repo.get_config('onyo.history.non-interactive')

    # test
    ret = subprocess.run(['onyo', 'history', '-I', assets[0]],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr
    fsck(repo)


@pytest.mark.repo_files(assets[0])
def test_history_config_invalid(repo: OnyoRepo) -> None:
    """
    Test that `onyo history -I` does error correctly when the history-tool does
    not exist.
    """
    # set to invalid
    repo.set_config('onyo.history.non-interactive', 'does-not-exist-in-path')
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Set non-existing: 'onyo.history.non-interactive'")

    # run history
    ret = subprocess.run(['onyo', 'history', '-I', assets[0]],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "'does-not-exist-in-path' was not found" in ret.stderr
    fsck(repo)


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_history_fake_noninteractive_stdout(repo: OnyoRepo, asset: str) -> None:
    """
    Test that the history tool can be reconfigured, so that `onyo history` can
    run commands different from the default options.
    """
    repo.set_config('onyo.history.non-interactive', '/usr/bin/env printf')
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Update config: 'onyo.history.non-interactive'")

    # test
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert Path(ret.stdout).resolve() == Path(asset).resolve()
    assert not ret.stderr
    fsck(repo)


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_history_fake_noninteractive_stderr(repo: OnyoRepo, asset: str) -> None:
    """
    Test that the history tool can be so reconfigured, that it prints into
    stderr instead of stdout.
    """
    repo.set_config('onyo.history.non-interactive', '/usr/bin/env printf >&2')
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Update config: 'onyo.history.non-interactive'")

    # test
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert Path(ret.stderr).resolve() == Path(asset).resolve()
    fsck(repo)


@pytest.mark.repo_files(assets[0])
@pytest.mark.parametrize('variant',
                         [{'cmd': '/usr/bin/env true', 'retval': 0},
                          {'cmd': '/usr/bin/env false', 'retval': 1},
                          {'cmd': 'git config --invalid-flag-oopsies',
                           'retval': 129}
                          ])
def test_history_fake_noninteractive_bubble_exit_code(repo: OnyoRepo, variant: dict) -> None:
    """
    Test that `onyo history` does bubble up the different exit codes that the
    tools configured return.
    """
    repo.set_config('onyo.history.non-interactive', variant['cmd'])
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Update config: 'onyo.history.non-interactive'")

    # test
    ret = subprocess.run(['onyo', 'history', '-I', assets[0]],
                         capture_output=True, text=True)
    assert ret.returncode == variant['retval']
    fsck(repo)
