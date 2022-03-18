#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
                        build_git_add_cmd,
                        get_git_root,
                        run_cmd,
                        prepare_directory
                        )

logging.basicConfig()
logger = logging.getLogger('onyo')

anchor_name = ".anchor"

def build_commit_cmd(file, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'anchor: " + file + "\'"]


def run_anchor(directory):
    filename = anchor_name
    if os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " anchor already exists.")
        sys.exit(0)
    run_cmd(create_asset_file_cmd(directory, filename))
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def create_asset_file_cmd(directory, filename):
    return "touch " + os.path.join(directory, filename)


def anchor(args):
    # set paths
    for folder in args.directory:
        directory = prepare_directory(folder)
        git_directory = get_git_root(directory)

        # create anchor file and add it
        created_file = run_anchor(directory)
        git_filepath = os.path.relpath(created_file, git_directory)

        # build commit command
        [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)

        # run commands
        run_cmd(commit_cmd, commit_msg)
