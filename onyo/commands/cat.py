#!/usr/bin/env python3

import logging
import os

from onyo.utils import run_cmd
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_cat_cmd(assets, onyo_root):
    list_of_cat_commands = []
    problem_str = ""
    for asset in assets:
        if os.path.isfile(os.path.join(onyo_root, asset)):
            list_of_cat_commands.append("cat \"" + os.path.join(onyo_root, asset) + "\"")
        elif os.path.isfile(asset):
            list_of_cat_commands.append("cat \"" + asset + "\"")
        elif os.path.isdir(os.path.join(onyo_root, asset)) or os.path.isdir(asset):
            problem_str = problem_str + "\nonyo cat expects file(s), but \"" + asset + "\" is a folder."
        else:
            problem_str = problem_str + "\n" + asset + " does not exist."
    if problem_str != "":
        logger.warning(problem_str)
    return list_of_cat_commands


def cat(args, onyo_root):

    # run onyo fsck for read only commands
    read_only_fsck(args, onyo_root, quiet=True)

    # check paths and build commands
    list_of_cat_commands = build_cat_cmd(args.asset, onyo_root)
    for command in list_of_cat_commands:
        # run commands
        output = run_cmd(command)
        print(output.strip())
