#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    run_cmd
)
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_tree_cmd(directory):
    if not os.path.isdir(directory):
        logger.error(directory + " does not exist.")
        sys.exit(1)
    return "tree \"" + directory + "\""


def prepare_arguments(sources, onyo_root):
    problem_str = ""
    list_of_sources = []
    # just a single path?
    single_source = "".join(sources)
    if os.path.isdir(single_source):
        return [single_source]
    elif os.path.isdir(os.path.join(onyo_root, single_source)):
        return [os.path.join(onyo_root, single_source)]
    # build paths
    for source in sources:
        current_source = source
        if not os.path.exists(current_source):
            current_source = os.path.join(onyo_root, source)
        # check if path exists
        if not os.path.exists(current_source):
            problem_str = problem_str + "\n" + source + " does not exist."
        elif not os.path.isdir(current_source):
            problem_str = problem_str + "\n" + source + " is not a directory."
        else:
            list_of_sources.append(current_source)
    if problem_str != "":
        logger.error(problem_str)
        sys.exit(1)
    return list_of_sources


def tree(args, onyo_root):
    # run onyo fsck for read only commands
    read_only_fsck(args, os.path.join(os.getcwd(), onyo_root), quiet=True)
    # check sources
    list_of_sources = prepare_arguments(args.directory, onyo_root)
    # build and run commands
    for source in list_of_sources:
        tree_command = build_tree_cmd(source)
        output = run_cmd(tree_command)
        print(output)
