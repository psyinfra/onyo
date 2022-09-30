#!/usr/bin/env python3

import logging
import os
import shutil
import sys
from pathlib import Path

from onyo.utils import get_config_value
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def sanitize_path(path, onyo_root):
    """
    Checks a path relative to onyo_root. If it does not exist, it will print
    an error and exit.

    Returns an absolute path on success.
    """
    if not path:
        path = './'

    full_path = Path(onyo_root, path).resolve()

    # check if path exists
    if not full_path.exists():
        logger.error(f"Cannot display the history of '{full_path}'. It does not exist.")
        logger.error("Exiting.")
        sys.exit(1)

    return full_path


def get_history_cmd(interactive, onyo_root):
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

    history_cmd = get_config_value(config_name, onyo_root)
    if not history_cmd:
        logger.error(f"'{config_name}' is unset and is required to display history.")
        logger.error("Please see 'onyo config --help' for information about how to set it. Exiting.")
        sys.exit(1)

    history_program = history_cmd.split(' ')[0]
    if not shutil.which(history_program):
        logger.error(f"'{history_cmd}' acquired from '{config_name}'.")
        logger.error(f"The program '{history_program}' was not found. Exiting.")
        sys.exit(1)

    return history_cmd


def history(args, onyo_root):
    """
    Display the history of an ``asset`` or ``directory``.

    Onyo detects whether an interactive TTY is in use, and will launch either an
    interactive display (default ``tig``) or a non-interactive one (default
    ``git log``) accordingly.

    The commands to display history are configurable using ``onyo config``.
    """
    read_only_fsck(args, onyo_root, quiet=True)

    # get the command and path
    history_cmd = get_history_cmd(args.interactive, onyo_root)
    path = sanitize_path(args.path, onyo_root)

    # run it
    orig_cwd = os.getcwd()
    try:
        os.chdir(onyo_root)
        status = os.system(f"{history_cmd} '{path}'")
    except:  # noqa: E722
        pass
    finally:
        os.chdir(orig_cwd)

    # covert the return status into a return code
    try:
        returncode = os.waitstatus_to_exitcode(status)
    except AttributeError:  # python <3.9
        returncode = os.WEXITSTATUS(status)

    # bubble up error retval
    if returncode != 0:
        exit(returncode)
