#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import run_cmd

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_tree_cmd(directory):
    if not os.path.isdir(directory):
        logger.error(directory + " does not exist.")
        sys.exit(0)
    return "tree " + directory


def tree(args):
    # build commands
    tree_command = build_tree_cmd(args.directory)

    # run commands
    output = run_cmd(tree_command)
    print(output)
