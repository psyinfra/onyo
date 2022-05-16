#!/usr/bin/env python3

import logging
import os

from onyo.utils import run_cmd
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_cat_cmd(files, onyo_root):
    list_of_cat_commands = []
    problem_str = ""
    for file in files:
        if os.path.isfile(os.path.join(onyo_root, file)):
            list_of_cat_commands.append("cat \"" + os.path.join(onyo_root, file) + "\"")
        elif os.path.isfile(file):
            list_of_cat_commands.append("cat \"" + file + "\"")
        else:
            problem_str = problem_str + "\n" + file + " does not exist."
    if problem_str != "":
        logger.warning(problem_str)
    return list_of_cat_commands


def cat(args, onyo_root):

    # run onyo fsck for read only commands
    read_only_fsck(args, onyo_root, quiet=True)

    # check paths and build commands
    list_of_cat_commands = build_cat_cmd(args.file, onyo_root)
    for command in list_of_cat_commands:
        # run commands
        output = run_cmd(command)
        print(output.strip())
