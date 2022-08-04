#!/usr/bin/env python3

import logging
import os
import sys
import configparser

from onyo.utils import (
    build_git_add_cmd,
    run_cmd,
    get_list_of_assets,
    edit_file
)
from onyo.commands.fsck import fsck

logging.basicConfig()
logger = logging.getLogger('onyo')

reserved_characters = ['_', '.']


def build_commit_cmd(file, onyo_root):
    return ["git -C " + onyo_root + " commit -m", "new asset.\n\n" + file]


def read_new_word(word_description):
    # read word for field from keyboard
    word = str(input(word_description))
    # if word contains reserved character, inform and read new word
    for char in reserved_characters:
        if char in word:
            logger.info(char + " is in list of reserved characters: " + ", ".join(reserved_characters))
            return read_new_word(word_description)
    # if enter pressed without input, read new word
    if len(word) == 0:
        return read_new_word(word_description)
    return word


def run_onyo_new(directory, template, non_interactive, onyo_root):
    # create an asset file, first without content
    filename = create_filename(onyo_root, template)
    if os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " asset already exists.")
        sys.exit(1)
    if template:
        run_cmd("cp \"" + template + "\" \"" + os.path.join(os.path.join(onyo_root, directory), filename) + "\"")
    else:
        run_cmd(create_asset_file_cmd(directory, filename))
    # open new file?
    if not non_interactive:
        edit_file(os.path.join(directory, filename), onyo_root, onyo_new=True)
    # add file to git
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def create_filename(onyo_root, template):
    words = []
    # build new name, read these words
    for field in ["type", "make", "model", "serial"]:
        word = read_new_word('<' + field + '>*:')
        words.append(word)
    filename = words[0] + "_" + words[1] + "_" + words[2] + "." + words[3]
    # check if the new filename is actually unique in onyo repository
    assets = get_list_of_assets(onyo_root)
    for asset in assets:
        if filename == asset[1]:
            logger.info(filename + " exists already in " + asset[0] + "\nCreate a new filename:")
            return create_filename(onyo_root, template)
    return filename


def create_asset_file_cmd(directory, filename):
    return "touch \"" + os.path.join(directory, filename) + "\""


def prepare_arguments(directory, template, onyo_root):
    directory = os.path.join(onyo_root, directory)
    # find the template to use:
    config = configparser.ConfigParser()
    config.read(os.path.join(onyo_root, ".onyo/config"))
    if not template:
        try:
            template = config['template']['default']
        except KeyError:
            pass
    template = os.path.join(onyo_root, os.path.join(".onyo/templates", template))
    problem_str = ""
    if not os.path.isfile(template):
        problem_str = problem_str + "\nTemplate file " + os.path.join(".onyo/templates", template) + " does not exist."
    if not os.path.isdir(directory):
        problem_str = problem_str + "\n" + directory + " is not a directory."
    if problem_str != "":
        logger.error(problem_str)
        sys.exit(1)
    return [directory, template]


def new(args, onyo_root):
    # run onyo fsck
    fsck(args, onyo_root, quiet=True)
    # set and check paths
    [directory, template] = prepare_arguments(args.directory, args.template, onyo_root)
    # create file for asset, fill in fields
    created_file = run_onyo_new(directory, template, args.non_interactive, onyo_root)
    git_filepath = os.path.relpath(created_file, onyo_root)
    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, onyo_root)
    # run commands
    run_cmd(commit_cmd, commit_msg)
