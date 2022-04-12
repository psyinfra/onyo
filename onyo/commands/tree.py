#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    run_cmd
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_tree_cmd(directory):
    if not os.path.isdir(directory):
        logger.error(directory + " does not exist.")
        sys.exit(1)
    return "tree \"" + directory + "\""


def check_sources(sources):
    problem_str = ""
    list_of_sources = []

    # just a single path?
    single_source = "".join(sources)
    if os.path.isdir(single_source):
        return [single_source]
    # check if any path for displaying tree exists
    onyo_default_repo = os.environ.get('ONYO_REPOSITORY_DIR')
    if len(sources) == 0 and onyo_default_repo is None:
        logger.error("No sources given and $ONYO_REPOSITORY_DIR not set.")
        sys.exit(1)
    elif onyo_default_repo is not None and os.path.isdir(os.path.join(onyo_default_repo, single_source)):
        return [os.path.join(onyo_default_repo, single_source)]

    # build paths
    for source in sources:
        current_source = os.path.join(os.getcwd(), source)
        # check if path is onyo or not
        if not os.path.exists(current_source) and onyo_default_repo is not None:
            current_source = os.path.join(onyo_default_repo, source)
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


def tree(args):

    # check sources
    list_of_sources = check_sources(args.directory)

    # build and run commands
    for source in list_of_sources:
        tree_command = build_tree_cmd(source)
        output = run_cmd(tree_command)
        print(output)
