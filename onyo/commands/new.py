#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    build_git_add_cmd,
    run_cmd,
    edit_file
)

logging.basicConfig()
logger = logging.getLogger('onyo')

reserved_characters = [".", "_"]


def build_commit_cmd(file, onyo_root):
    return ["git -C " + onyo_root + " commit -m", "new asset.\n\n" + file]


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


def run_onyo_new(directory, non_interactive):
    type_str = read_new_word('<type>*:')
    make_str = read_new_word('<make>*:')
    model_str = read_new_word('<model*>:')
    serial_str = read_new_word('<serial*>:', char_checks=False)
    filename = create_filename(type_str, make_str, model_str, serial_str)
    if os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " asset already exists.")
        sys.exit(1)
    run_cmd(create_asset_file_cmd(directory, filename))
    if not non_interactive:
        edit_file(os.path.join(directory, filename))
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def create_filename(type_str, make_str, model_str, serial_str):
    filename = type_str + "_" + make_str + "_" + model_str + "." + serial_str
    return filename


def create_asset_file_cmd(directory, filename):
    return "touch \"" + os.path.join(directory, filename) + "\""


def prepare_arguments(directory, onyo_root):
    directory = os.path.join(onyo_root, directory)
    if not os.path.isdir(directory):
        logger.error(directory + " is not a directory.")
        sys.exit(1)
    return directory


def new(args, onyo_root):
    # set and check paths
    directory = prepare_arguments(args.directory, onyo_root)

    # create file for asset, fill in fields
    created_file = run_onyo_new(directory, args.non_interactive)
    git_filepath = os.path.relpath(created_file, onyo_root)

    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, onyo_root)

    # run commands
    run_cmd(commit_cmd, commit_msg)
