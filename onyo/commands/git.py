#!/usr/bin/env python3

import logging

from onyo.utils import (
    get_git_root,
    run_cmd,
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_command(command, git_directory):
    cmd_str = ""
    for arg in command:
        if " " in arg:
            cmd_str += " \"" + arg + "\""
        else:
            cmd_str += " " + arg
    return " ".join(["git -C \"" + git_directory + "\" " + cmd_str])


def git(args):
    # set paths
    git_directory = get_git_root(args.directory)

    # build command
    command = build_command(args.command, git_directory)

    # run commands
    print(run_cmd(command))
