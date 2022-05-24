#!/usr/bin/env python3

import logging
import os
import sys
import yaml

from onyo.utils import (
    build_git_add_cmd,
    run_cmd,
    get_list_of_assets,
    edit_file
)
from onyo.commands.fsck import fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(file, onyo_root):
    return ["git -C " + onyo_root + " commit -m", "new asset.\n\n" + file]


def read_new_word(word_description, reserved_characters):
    # read word for field from keyboard
    word = str(input(word_description))
    # if word contains reserved character, inform and read new word
    for char in reserved_characters:
        if char in word:
            logger.info(char + " is in list of reserved characters: " + ", ".join(reserved_characters))
            return read_new_word(word_description, reserved_characters)
    # if enter pressed without input, read new word
    if len(word) == 0:
        return read_new_word(word_description, reserved_characters)
    return word


def run_onyo_new(directory, template_contents, non_interactive, onyo_root):
    # create an asset file, first without content
    filename = create_filename(onyo_root, template_contents)
    if os.path.exists(os.path.join(directory, filename)):
        logger.error(os.path.join(directory, filename) + " asset already exists.")
        sys.exit(1)
    run_cmd(create_asset_file_cmd(directory, filename))
    # read values for asset, if given, and write them into the new asset file
    value_fields = []
    values = {}
    try:
        value_fields = template_contents['value_fields']
    except KeyError:
        pass
    if value_fields != []:
        for field in value_fields:
            reserved_characters = []
            try:
                reserved_characters = [str(x) for x in str(field['reserved_characters'])]
            except KeyError:
                pass
            word = read_new_word('<' + field['name'] + '>*:', reserved_characters)
            values[field['name']] = word
        # actual writing in file:
        file = open(os.path.join(directory, filename), "w")
        yaml.dump(values, file)
        file.close()
    # open editor after creating/writing file, if not called non-interactive
    if not non_interactive:
        edit_file(os.path.join(directory, filename), onyo_root)
    # add file to git
    git_add_cmd = build_git_add_cmd(directory, filename)
    run_cmd(git_add_cmd)
    return os.path.join(directory, filename)


def create_filename(onyo_root, template_contents):
    words = []
    filename = template_contents['name']
    for field in template_contents['name_fields']:
        reserved_characters = []
        try:
            reserved_characters = [str(x) for x in str(field['reserved_characters'])]
        except KeyError:
            pass
        word = read_new_word('<' + field['name'] + '>*:', reserved_characters)
        words.append(word)
        if field['name'] in filename:
            filename = filename.replace("<" + field['name'] + ">", word)
    # check if the new filename is actually unique in onyo repository
    assets = get_list_of_assets(onyo_root)
    for asset in assets:
        if filename == asset[1]:
            logger.info(filename + " exists already in " + asset[0] + "\nCreate a new filename:")
            return create_filename(onyo_root, template_contents)
    return filename


def create_asset_file_cmd(directory, filename):
    return "touch \"" + os.path.join(directory, filename) + "\""


def prepare_arguments(directory, template, onyo_root):
    directory = os.path.join(onyo_root, directory)
    template = os.path.join(onyo_root, os.path.join(".onyo/templates", template))
    template_contents = ""
    problem_str = ""
    if not os.path.isfile(template):
        problem_str = problem_str + "\nTemplate file " + os.path.join(".onyo/templates", template) + " does not exist."
    with open(template, "r") as stream:
        try:
            template_contents = yaml.safe_load(stream)
        except yaml.YAMLError:
            problem_str = problem_str + "\nTemplate file " + os.path.join(".onyo/templates", template) + " can't be loaded."
    if not os.path.isdir(directory):
        problem_str = problem_str + "\n" + directory + " is not a directory."
    if problem_str != "":
        logger.error(problem_str)
        sys.exit(1)
    return [directory, template_contents]


def new(args, onyo_root):
    # run onyo fsck
    fsck(args, onyo_root, quiet=True)
    # set and check paths
    [directory, template_contents] = prepare_arguments(args.directory, args.template, onyo_root)
    # create file for asset, fill in fields
    created_file = run_onyo_new(directory, template_contents, args.non_interactive, onyo_root)
    git_filepath = os.path.relpath(created_file, onyo_root)
    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, onyo_root)
    # run commands
    run_cmd(commit_cmd, commit_msg)
