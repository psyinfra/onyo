#!/usr/bin/env python3

import logging
import os

from onyo.utils import run_cmd

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_cat_cmd(files):
    list_of_cat_commands = []
    problem_str = ""
    onyo_repository_dir = os.environ.get('ONYO_REPOSITORY_DIR')
    for file in files:
        if os.path.isfile(file):
            list_of_cat_commands.append("cat \"" + file + "\"")
        elif not os.path.isfile(file) and onyo_repository_dir is not None:
            list_of_cat_commands.append("cat \"" + os.path.join(onyo_repository_dir, file) + "\"")
        else:
            problem_str = problem_str + "\n" + file + " does not exist."
    if problem_str != "":
        logger.warning(problem_str)
    return list_of_cat_commands


def cat(args):
    # check paths and build commands
    list_of_cat_commands = build_cat_cmd(args.file)
    for command in list_of_cat_commands:
        # run commands
        output = run_cmd(command)
        print(output.strip())
