#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    build_git_add_cmd,
    run_cmd
)
from onyo.commands.fsck import fsck

logging.basicConfig()
logger = logging.getLogger('onyo')

anchor_name = ".anchor"


def build_commit_cmd(folders, onyo_root):
    return ["git -C \"" + onyo_root + "\" commit -m", "new folder(s).\n\n" + "\n".join(folders)]


def run_mkdir(onyo_root, new_directory):
    filename = anchor_name
    full_directory = os.path.join(onyo_root, new_directory)
    if os.path.isdir(full_directory):
        logger.error(full_directory + " exists already.")
        sys.exit(1)
    # run the actual commands, for creating a folder, anchor it, add it to git
    current_directory = onyo_root
    for folder in os.path.normpath(new_directory).split(os.path.sep):
        current_directory = os.path.join(current_directory, folder)
        if os.path.isdir(current_directory):
            continue
        run_cmd("mkdir \"" + current_directory + "\"")
        run_cmd("touch \"" + os.path.join(current_directory, filename) + "\"")
        git_add_cmd = build_git_add_cmd(onyo_root, os.path.join(current_directory, filename))
        run_cmd(git_add_cmd)
    return full_directory


def get_existing_subpath(directory, onyo_root):
    existing_path = onyo_root
    missing_path = ""
    for folder in os.path.normpath(directory).split(os.path.sep):
        if os.path.isdir(os.path.join(existing_path, folder)):
            existing_path = os.path.join(existing_path, folder)
        else:
            missing_path = os.path.join(missing_path, folder)
    return [existing_path, missing_path]


def prepare_arguments(directories, onyo_root):
    problem_str = ""
    list_of_folders = []
    for folder in directories:
        [existing_path, missing_path] = get_existing_subpath(folder, onyo_root)
        if missing_path == "":
            problem_str = problem_str + "\n" + existing_path + " already exists."
        else:
            list_of_folders.append(folder)
    if problem_str != "":
        logger.error(problem_str + "\nNo folders created.")
        sys.exit(1)
    return list(dict.fromkeys(list_of_folders))


def mkdir(args, onyo_root):
    # run onyo fsck
    fsck(args, onyo_root, quiet=True)
    # check and set paths
    list_of_folders = prepare_arguments(args.directory, onyo_root)
    # loop over folders and create them with an anchor file
    for folder in list_of_folders:
        run_mkdir(onyo_root, folder)
    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(list_of_folders, onyo_root)
    # run commands
    run_cmd(commit_cmd, commit_msg)
