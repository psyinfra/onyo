#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    build_git_add_cmd,
    get_git_root,
    run_cmd
)

logging.basicConfig()
logger = logging.getLogger('onyo')

anchor_name = ".anchor"


def build_commit_cmd(folder, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'new folder: " + folder + "\'"]


def run_mkdir(git_directory, new_directory):
    filename = anchor_name
    full_directory = os.path.join(git_directory, new_directory)
    if os.path.isdir(full_directory):
        logger.error(full_directory + " exists already.")
        sys.exit(1)
    # run the actual commands, for creating a folder, anchor it, add it to git
    current_directory = git_directory
    for folder in os.path.normpath(new_directory).split(os.path.sep):
        current_directory = os.path.join(current_directory, folder)
        if os.path.isdir(current_directory):
            continue
        run_cmd("mkdir " + current_directory)
        run_cmd("touch " + os.path.join(current_directory, filename))
        git_add_cmd = build_git_add_cmd(git_directory, os.path.join(current_directory, filename))
        run_cmd(git_add_cmd)
    return full_directory


def get_existing_subpath(directory):
    if os.getenv('ONYO_REPOSITORY_DIR') is not None:
        existing_path = os.getenv('ONYO_REPOSITORY_DIR')
    else:
        existing_path = os.getcwd()
    missing_path = ""
    for folder in os.path.normpath(directory).split(os.path.sep):
        if os.path.isdir(os.path.join(existing_path, folder)):
            existing_path = os.path.join(existing_path, folder)
        else:
            missing_path = os.path.join(missing_path, folder)
    return [existing_path, missing_path]


def check_directories(directories):
    problem_str = ""
    for folder in directories:
        [existing_path, missing_path] = get_existing_subpath(folder)
        if missing_path == "":
            problem_str = problem_str + "\n" + existing_path + " already exists."
    if problem_str != "":
        logger.error(problem_str + "\nNo folders created.")
        sys.exit(1)


def mkdir(args):

    check_directories(args.directory)

    for folder in args.directory:
        # set paths
        [existing_path, missing_path] = get_existing_subpath(folder)
        git_directory = get_git_root(existing_path)
        new_directory = os.path.join(existing_path, missing_path).replace(git_directory + os.path.sep, "")

        # create anchor file and add it
        created_directory = run_mkdir(git_directory, new_directory)
        git_folder_path = os.path.relpath(created_directory, git_directory)

        # build commit command
        [commit_cmd, commit_msg] = build_commit_cmd(git_folder_path, git_directory)

        # run commands
        run_cmd(commit_cmd, commit_msg)
