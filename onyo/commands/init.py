#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
                        build_git_add_cmd,
                        is_git_dir,
                        run_cmd
                        )
logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(directory):
    return ["git -C " + directory + " commit -m",
            "\'initialize onyo repository\'"]


def build_git_init_cmd(directory):
    if is_git_dir(directory):
        logger.error(directory + " is already a git-repository.")
        sys.exit(0)
    return "git init --initial-branch=master " + directory


def build_onyo_init_cmd(directory):
    if os.path.isdir(os.path.join(directory + "/.onyo")):
        logger.error(os.path.join(directory + "/.onyo") + " already exists.")
        sys.exit(0)
    return "mkdir " + os.path.join(directory + "/.onyo")


def create_file_cmd(directory):
    return "touch " + os.path.join(directory + "/.onyo/onyo.txt")


def init(args):
    # build commands
    git_init_command = build_git_init_cmd(args.directory)
    onyo_init_command = build_onyo_init_cmd(args.directory)
    create_file_command = create_file_cmd(args.directory)
    git_add_command = build_git_add_cmd(args.directory, ".onyo/")
    [commit_cmd, commit_msg] = build_commit_cmd(args.directory)

    # run commands
    run_cmd(git_init_command)
    run_cmd(onyo_init_command)
    run_cmd(create_file_command)
    run_cmd(git_add_command)
    run_cmd(commit_cmd, commit_msg)