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


def build_commit_cmd(file, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'new " + file + "\'"]


def run_onyo_new(directory):
    type_str = str(input('<type>*:'))
    make_str = str(input('<make>*:'))
    model_str = str(input('<model*>:'))
    serial_str = str(input('<serial*>:'))
    filename = create_filename(type_str, make_str, model_str, serial_str)
    if os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " asset already exists.")
        sys.exit(0)
    run_cmd(create_asset_file_cmd(directory, filename))
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def create_filename(type_str, make_str, model_str, serial_str):
    filename = type_str + "_" + make_str + "_" + model_str + "." + serial_str
    return filename


def create_asset_file_cmd(directory, filename):
    return "touch " + os.path.join(directory, filename)


def new(args):
    # set paths
    directory = prepare_directory(args.directory)
    git_directory = get_git_root(directory)

    # create file for asset, fill in fields
    created_file = run_onyo_new(directory)
    git_filepath = os.path.relpath(created_file, git_directory)

    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)

    # run commands
    run_cmd(commit_cmd, commit_msg)
