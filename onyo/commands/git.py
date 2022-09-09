#!/usr/bin/env python3

import logging

from onyo.utils import (
    run_cmd
)
from onyo.commands.fsck import fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_command(command, onyo_root):
    cmd_str = ""
    for arg in command:
        if " " in arg:
            cmd_str += " \"" + arg + "\""
        else:
            cmd_str += " " + arg
    return " ".join(["git -C \"" + onyo_root + "\" " + cmd_str])


def git(args, onyo_root):
    """
    Pass ``git-command-args`` as arguments to ``git``, using the Onyo repository
    as the git repository.
    """

    # run onyo fsck
    fsck(args, onyo_root, quiet=True)
    # build command
    command = build_command(args.command, onyo_root)
    # run commands
    print(run_cmd(command))
