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
    return ["git -C " + git_directory + " commit -m",
            "\'remove anchor: " + file + "\'"]


def run_unanchor(directory):
    filename = anchor_name
    if not os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " has no anchor.")
        sys.exit(0)
    run_cmd("rm -f " + os.path.join(directory, filename))
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def unanchor(args):
    for folder in args.directory:
        # set paths
        directory = prepare_directory(folder)
        git_directory = get_git_root(directory)

        # remove anchor file and add it
        created_file = run_unanchor(directory)
        git_filepath = os.path.relpath(created_file, git_directory)

        # build commit command
        [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)

        # run commands
        run_cmd(commit_cmd, commit_msg)
