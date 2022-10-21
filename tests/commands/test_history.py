import subprocess
from pathlib import Path


# NOTE: the output of `onyo history` is not tested for formatting or content, as
#       the commands called by `onyo history` are user-configurable. Instead, it
#       is tested for whether the output of the underlying command is unaltered.
def test_onyo_init():
    ret = subprocess.run(["onyo", "init"])
    assert ret.returncode == 0

    create_dirs = ['subdir',
                   's p a c e s',
                   's p a/c e s',
                   ]

    # create dirs
    ret = subprocess.run(['onyo', 'mkdir'] + create_dirs)
    assert ret.returncode == 0

    # create files
    Path('a').touch()
    Path('subdir/b').touch()
    Path('s p a c e s/c').touch()
    Path('s p a/c e s/1 2').touch()

    # add and commit
    ret = subprocess.run(['git', 'add', '.'])
    assert ret.returncode == 0
    ret = subprocess.run(['git', 'commit', '-m', 'populated for tests'])
    assert ret.returncode == 0


def test_history_noninteractive():
    ret = subprocess.run(["onyo", "history", "-I"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


def test_history_noninteractive_file():
    ret = subprocess.run(["onyo", "history", "-I", "a"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


def test_history_noninteractive_dir():
    ret = subprocess.run(["onyo", "history", "-I", "subdir/"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


def test_history_noninteractive_spaces():
    ret = subprocess.run(["onyo", "history", "-I", "s p a c e s/"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr

    # subdir
    ret = subprocess.run(["onyo", "history", "-I", "s p a/c e s/1 2"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


def test_history_noninteractive_not_exist():
    ret = subprocess.run(["onyo", "history", "-I", "does_not_exist"],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr

    # subdir
    ret = subprocess.run(["onyo", "history", "-I", "subdir/does_not_exist"],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


def test_history_noninteractive_too_many_args():
    ret = subprocess.run(["onyo", "history", "-I", "a", "subdir/b"],
                         capture_output=True, text=True)
    assert ret.returncode != 0
    assert not ret.stdout
    assert ret.stderr


# NOTE: interactive cannot be tested directly, as onyo detects whether it's
#       connected to a TTY.
def test_history_interactive_fallback():
    ret = subprocess.run(["onyo", "history", "subdir/b"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout
    assert not ret.stderr


# Error when no config flag is found
def test_history_config_unset():
    # git is already unset
    assert 'onyo.history.non-interactive' not in Path('.git/config').read_text()
    # unset onyo
    ret = subprocess.run(["onyo", "config", "--unset", "onyo.history.non-interactive"],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # run history
    ret = subprocess.run(["onyo", "history", "-I", "subdir/b"],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


def test_history_config_invalid():
    # git is already unset
    assert 'onyo.history.non-interactive' not in Path('.git/config').read_text()
    # set to invalid
    ret = subprocess.run(["onyo", "config", "onyo.history.non-interactive", "does-not-exist-in-path"],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # run history
    ret = subprocess.run(["onyo", "history", "-I", "subdir/b"],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "'does-not-exist-in-path' was not found" in ret.stderr


# Reconfigure the history command to tickle some other functionality we're
# interested in.
def test_history_fake_noninteractive_stdout():
    ret = subprocess.run(["onyo", "config", "onyo.history.non-interactive", "/bin/printf"],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # single file
    ret = subprocess.run(["onyo", "history", "-I", "a"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert Path(ret.stdout).resolve() == Path('a').resolve()
    assert not ret.stderr

    # spaces
    ret = subprocess.run(["onyo", "history", "-I", "s p a/c e s/1 2"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert Path(ret.stdout).resolve() == Path('s p a/c e s/1 2').resolve()
    assert not ret.stderr


def test_history_fake_noninteractive_stderr():
    ret = subprocess.run(["onyo", "config", "onyo.history.non-interactive", "/bin/printf >&2"],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # single file
    ret = subprocess.run(["onyo", "history", "-I", "a"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert Path(ret.stderr).resolve() == Path('a').resolve()

    # spaces
    ret = subprocess.run(["onyo", "history", "-I", "s p a/c e s/1 2"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stdout
    assert Path(ret.stderr).resolve() == Path('s p a/c e s/1 2').resolve()


def test_history_fake_noninteractive_bubble_exit_code():
    # success
    ret = subprocess.run(["onyo", "config", "onyo.history.non-interactive", "/bin/true"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    ret = subprocess.run(["onyo", "history", "-I", "a"],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # error
    ret = subprocess.run(["onyo", "config", "onyo.history.non-interactive", "git config --invalid-flag-oopsies"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    ret = subprocess.run(["onyo", "history", "-I", "a"],
                         capture_output=True, text=True)
    # Passing invalid flags to git causes it to exit with "129".
    assert ret.returncode == 129

# TODO: test from outside the repo (-C)
