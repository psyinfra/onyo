#!/usr/bin/env python3

import logging
import os
import sys

from git import Repo

from onyo.utils import (
                        build_git_add_cmd,
                        get_full_filepath,
                        get_git_root,
                        run_cmd
                        )

logging.basicConfig()
logger = logging.getLogger('onyo')


def get_editor():
    editor = os.environ.get('EDITOR')
    if editor is None:
        editor = 'nano'
    return editor


def build_commit_cmd(file, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'edit " + file + "\'"]


def edit_file_cmd(file):
    if not os.path.isfile(file):
        logger.error(file + " does not exist.")
        sys.exit(0)
    os.system(get_editor() + " " + file)
    return


def edit(args):

    # folder that contains git, by environment var or by position of file
    git_directory = get_git_root(args.file)
    # wants to get the full filepath, and the path relative from git_directory
    full_filepath = get_full_filepath(git_directory, args.file)
    git_filepath = os.path.relpath(full_filepath, git_directory)

    # check if file is in git. There might be a better test, since this just
    # tests for "untracked", not for newest version.
    run_output = run_cmd("git -C " + git_directory + " ls-tree -r HEAD ")
    if git_filepath not in run_output:
        logger.error(git_filepath + " is not in onyo.")
        sys.exit(0)

    # change file
    edit_file_cmd(full_filepath)

    # TODO: check here if yaml still works

    # check if changes happened and add+commit them
    repo = Repo(git_directory)
    changedFiles = [item.a_path for item in repo.index.diff(None)]
    if len(changedFiles) != 0:
        git_add_cmd = build_git_add_cmd(git_directory, git_filepath)

        [commit_cmd, commit_msg] = build_commit_cmd(git_filepath,
                                                    git_directory)

        # run commands
        run_cmd(git_add_cmd)
        run_cmd(commit_cmd, commit_msg)
    else:
        logger.error("no changes made.")
        sys.exit(0)
