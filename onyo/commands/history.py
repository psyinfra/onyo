from __future__ import annotations
import logging
import os
import shutil
import sys
from pathlib import Path
from shlex import quote
from typing import TYPE_CHECKING

from onyo import Repo, OnyoInvalidRepoError

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def sanitize_path(path: str, opdir: str) -> Path:
    """
    Checks a path relative to opdir. If it does not exist, it will print an
    error and exit.

    Returns an absolute path on success.
    """
    if not path:
        path = './'

    full_path = Path(opdir, path).resolve()

    # check if path exists
    if not full_path.exists():
        print(f"Cannot display the history of '{full_path}'. It does not exist.", file=sys.stderr)
        print("Exiting.", file=sys.stderr)
        sys.exit(1)

    return full_path


def get_history_cmd(interactive: bool, repo: Repo) -> str:
    """
    Get the command used to display history. The appropriate one is selected
    according to the interactive mode, and basic checks are performed for
    validity.

    Returns the command on success.
    """
    history_cmd = None
    config_name = 'onyo.history.interactive'

    if not interactive or not sys.stdout.isatty():
        config_name = 'onyo.history.non-interactive'

    history_cmd = repo.get_config(config_name)
    if not history_cmd:
        print(f"'{config_name}' is unset and is required to display history.", file=sys.stderr)
        print("Please see 'onyo config --help' for information about how to set it. Exiting.", file=sys.stderr)
        sys.exit(1)

    history_program = history_cmd.split()[0]
    if not shutil.which(history_program):
        print(f"'{history_cmd}' acquired from '{config_name}'.", file=sys.stderr)
        print(f"The program '{history_program}' was not found. Exiting.", file=sys.stderr)
        sys.exit(1)

    return history_cmd


def history(args: argparse.Namespace, opdir: str) -> None:
    """
    Display the history of an ``asset`` or ``directory``.

    Onyo detects whether an interactive TTY is in use, and will launch either an
    interactive display (default ``tig``) or a non-interactive one (default
    ``git log``) accordingly.

    The commands to display history are configurable using ``onyo config``.
    """
    repo = None
    try:
        repo = Repo(opdir, find_root=True)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    # get the command and path
    path = sanitize_path(args.path, opdir)
    history_cmd = get_history_cmd(args.interactive, repo)

    # run it
    orig_cwd = os.getcwd()
    status = 0
    try:
        os.chdir(opdir)
        status = os.system(f"{history_cmd} {quote(str(path))}")
    except:  # noqa: E722
        pass
    finally:
        os.chdir(orig_cwd)

    # covert the return status into a return code
    returncode = os.waitstatus_to_exitcode(status)

    # bubble up error retval
    if returncode != 0:
        exit(returncode)
