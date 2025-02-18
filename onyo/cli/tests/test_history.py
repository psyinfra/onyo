from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import fsck

if TYPE_CHECKING:
    from typing import List

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
    r"""Default non-interactive history prints to stdout and not stderr."""

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
    r"""Non-existing assets print to stderr and return an error code."""

    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert ret.returncode != 0
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
    r"""Multiple input arguments are not allowed."""

    ret = subprocess.run(['onyo', 'history', '-I', *variant],
                         capture_output=True, text=True)
    assert ret.returncode != 0
    assert not ret.stdout
    assert ret.stderr
    fsck(repo)


@pytest.mark.repo_files(assets[0])
def test_history_interactive_fallback(repo: OnyoRepo) -> None:
    r"""``--non-interactive`` works.

    Interactive mode cannot be tested directly, as onyo detects whether it's
    connected to a TTY.
    """
    ret = subprocess.run(['onyo', 'history', assets[0]],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr
    fsck(repo)


@pytest.mark.repo_files(assets[0])
def test_history_config_unset(repo: OnyoRepo) -> None:
    r"""Error when no tool is configured."""

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
    r"""Error when the history tool does not exist."""

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
    r"""The history tool can be reconfigured."""

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
    r"""The configured tool controls printing to stdout vs stderr."""

    # configure to simply print to stdout
    repo.set_config('onyo.history.non-interactive', '/usr/bin/env printf >&1')
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Update config: 'onyo.history.non-interactive'")

    # test
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert Path(ret.stdout).resolve() == Path(asset).resolve()

    # configure to simply print to stderr
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
                          {'cmd': '/usr/bin/sh -c "exit 42"', 'retval': 42},
                          {'cmd': 'git config --invalid-flag', 'retval': 129},
                          ])
def test_history_fake_noninteractive_bubble_exit_code(repo: OnyoRepo, variant: dict) -> None:
    r"""Bubble up exit codes unaltered from history tool."""

    repo.set_config('onyo.history.non-interactive', variant['cmd'])
    repo.commit(paths=repo.dot_onyo / 'config',
                message="Update config: 'onyo.history.non-interactive'")

    # test
    ret = subprocess.run(['onyo', 'history', '-I', assets[0]],
                         capture_output=True, text=True)
    assert ret.returncode == variant['retval']
    fsck(repo)
