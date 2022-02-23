#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

from git import Repo, exc

logging.basicConfig()
logger = logging.getLogger('onyo')


def is_git_dir(directory):
    try:
        Repo(directory).git_dir
        return True
    except exc.InvalidGitRepositoryError:
        return False


def run_cmd(cmd, comment=""):
    if comment != "":
        run_process = subprocess.Popen(cmd.split() + [comment],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True)
    else:
        run_process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, universal_newlines=True)
    run_output, run_error = run_process.communicate()
    if (run_error != ""):
        logger.error(run_error)
        sys.exit(0)
    else:
        logger.info(cmd + " " + comment)


def build_commit_cmd(file, git_directory):
    return ["git -C "+ git_directory + " commit -m", "\'new " + file + "\'"]


def run_onyo_new(location):
    type_str = str(input('<type>*:'))
    make_str = str(input('<make>*:'))
    model_str = str(input('<model*>:'))
    serial_str = str(input('<serial*>:'))
    filename = create_filename(type_str, make_str, model_str, serial_str)
    run_cmd(create_asset_file_cmd(location, filename))
    git_add_cmd = build_git_add_cmd(filename, location)
    run_cmd(git_add_cmd)
    return os.path.join(location, filename)


def create_filename(type_str, make_str, model_str, serial_str):
    filename = type_str + "_" + make_str + "_" + model_str + "." + serial_str
    return filename


def build_git_add_cmd(file, directory):
    return "git -C " + directory + " add " + file


def create_asset_file_cmd(directory, filename):
    return "touch " + os.path.join(directory, filename)


def get_location(location):
    if not os.path.isdir(location):
        onyo_dir = os.environ.get('ONYO_REPOSITORY_DIR')
        if onyo_dir != None:
            location = os.path.join(onyo_dir, location)
        else:
            logger.error(location + " does not exist.")
            sys.exit(0)
    return location


def get_git_root(path):
    # first checks if file is in git from current position
    try:
        git_repo = Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        return git_root
    # otherwise checks if given file relative to $ONYO_REPOSITORY_DIR is in a
    # git repository
    except (exc.NoSuchPathError, exc.InvalidGitRepositoryError):
        onyo_path = os.environ.get('ONYO_REPOSITORY_DIR')
        if onyo_path == None:
            logger.error(path + " is no onyo repository.")
            sys.exit(0)
        elif not is_git_dir(onyo_path):
            logger.error(path + " is no onyo repository.")
            sys.exit(0)

        git_repo = Repo(os.path.join(path, onyo_path), search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        return git_root


def get_full_filepath(git_directory, file):
    full_filepath = os.path.join(git_directory, file)
    if not os.path.isfile(full_filepath):
        full_filepath = os.path.join(git_directory, os.getcwd())
        full_filepath = os.path.join(full_filepath, file)
    if not os.path.isfile(full_filepath):
        logger.error(file + " not found.")
        sys.exit(0)
    return full_filepath


def new(args):
    # set paths
    git_directory = get_git_root(args.location)
    location = os.path.join(git_directory, args.location)

    # create file for asset, fill in fields
    created_file = run_onyo_new(location)
    git_filepath = os.path.relpath(created_file, git_directory)

    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)

    # run commands
    run_cmd(commit_cmd, commit_msg)
