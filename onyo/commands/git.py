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
    # run onyo fsck
    fsck(args, onyo_root, quiet=True)
    # if "onyo git -C <dir>" is called
    if args.directory is not None:
        onyo_root = args.directory
    # build command
    command = build_command(args.command, onyo_root)
    # run commands
    print(run_cmd(command))
