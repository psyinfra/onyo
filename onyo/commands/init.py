#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
                        build_git_add_cmd,
                        is_git_dir,
                        get_git_root,
                        run_cmd
                        )
logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(directory):
    return ["git -C " + directory + " commit -m",
            "\'initialize onyo repository\'"]


def build_git_init_cmd(directory):
    if is_git_dir(directory) and os.path.isdir(directory + "/.onyo"):
        logger.info(directory + " has already a onyo configuration directory " +
            "and is a git repository.")
        sys.exit(0)
    elif is_git_dir(directory):
        logger.info(directory + " is already a  git repository.")
        return None
    return "git init --initial-branch=master " + directory


def build_onyo_init_cmd(directory):
    if os.path.isdir(os.path.join(directory + "/.onyo")) and not os.path.isdir(os.path.join(directory + "/.git")):
        logger.error(directory + " has an onyo configuration directory, but " +
                "is not a git repository. Either delete the onyo " +
                "configuration directory or use git init to manually " +
                "initialize as git repository.")
        sys.exit(0)
    elif os.path.isdir(os.path.join(directory + "/.onyo")):
        logger.error(directory + " has already an onyo configuration directory.")
        sys.exit(0)
    return "mkdir " + os.path.join(directory + "/.onyo")


def create_file_cmd(directory):
    return "touch " + os.path.join(directory + "/.onyo/.anchor")


def init(args):
    # build commands
    git_init_command = build_git_init_cmd(args.directory)
    onyo_init_command = build_onyo_init_cmd(args.directory)
    create_file_command = create_file_cmd(args.directory)
    git_add_command = build_git_add_cmd(args.directory, ".onyo/")
    [commit_cmd, commit_msg] = build_commit_cmd(args.directory)

    # run commands
    if git_init_command is not None:
        run_cmd(git_init_command)
    run_cmd(onyo_init_command)
    run_cmd(create_file_command)
    run_cmd(git_add_command)
    run_cmd(commit_cmd, commit_msg)
    logger.info(commit_msg + ": " + get_git_root(args.directory))
