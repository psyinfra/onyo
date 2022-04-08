#!/usr/bin/env python3

import logging
import os
import sys

from git import Repo

from onyo.utils import (
    build_git_add_cmd,
    get_full_filepath,
    get_git_root,
    run_cmd,
    edit_file
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(file, git_directory):
    return ["git -C \"" + git_directory + "\" commit -m", "\'edit " + file + "\'"]


def edit(args):
    # set paths
    git_directory = get_git_root(args.file)
    full_filepath = get_full_filepath(git_directory, args.file)
    # path relative from git root dir
    git_filepath = os.path.relpath(full_filepath, git_directory)

    # check if file is in git
    run_output = run_cmd("git -C \"" + git_directory + "\" ls-tree -r HEAD ")
    if git_filepath not in run_output:
        logger.error(git_filepath + " is not in onyo.")
        sys.exit(1)

    # change file
    edit_file(full_filepath)

    # check if changes happened and add+commit them
    repo = Repo(git_directory)
    changedFiles = [item.a_path for item in repo.index.diff(None)]
    if len(changedFiles) != 0:
        # build commands
        git_add_cmd = build_git_add_cmd(git_directory, git_filepath)
        [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)
        # run commands
        run_cmd(git_add_cmd)
        run_cmd(commit_cmd, commit_msg)
    else:
        logger.error("no changes made.")
        sys.exit(1)
