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

reserved_characters = [".", "_"]


def build_commit_cmd(file, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'new \"" + file + "\"\'"]


def read_new_word(word_description, char_checks=True):
    # read word for field from keyboard
    word = str(input(word_description))
    # if checks=True and field contains one of the reserved characters,
    # read new word.
    if char_checks:
        for char in reserved_characters:
            if char in word:
                logger.info(char + " is in list of reserved characters: " + ", ".join(reserved_characters))
                return read_new_word(word_description, char_checks=char_checks)
    # if enter pressed without input, read new word
    if len(word) == 0:
        return read_new_word(word_description, char_checks=char_checks)
    return word


def run_onyo_new(directory):
    type_str = read_new_word('<type>*:')
    make_str = read_new_word('<make>*:')
    model_str = read_new_word('<model*>:')
    serial_str = read_new_word('<serial*>:', char_checks=False)
    filename = create_filename(type_str, make_str, model_str, serial_str)
    if os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " asset already exists.")
        sys.exit(1)
    run_cmd(create_asset_file_cmd(directory, filename))
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def create_filename(type_str, make_str, model_str, serial_str):
    filename = type_str + "_" + make_str + "_" + model_str + "." + serial_str
    return filename


def create_asset_file_cmd(directory, filename):
    return "touch \"" + os.path.join(directory, filename) + "\""


def new(args):

    # set paths
    directory = prepare_directory(args.directory)
    if not os.path.isdir(directory):
        logger.error(directory + " is not a directory.")
        sys.exit(1)
    git_directory = get_git_root(directory)

    # create file for asset, fill in fields
    created_file = run_onyo_new(directory)
    git_filepath = os.path.relpath(created_file, git_directory)

    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)

    # run commands
    run_cmd(commit_cmd, commit_msg)
