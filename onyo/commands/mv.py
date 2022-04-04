#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    get_git_root,
    run_cmd
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_mv_cmd(git_path, source, destination, force, rename):
    if (os.path.basename(destination) != os.path.basename(source) and not
            (rename or os.path.isdir(source))):
        logger.error(os.path.basename(source) + " -> " +
                     os.path.basename(destination) + " no renaming allowed.")
        sys.exit(1)
    if os.path.isfile(os.path.join(git_path, destination)):
        if force:
            return "git -C " + git_path + " mv -f \"" + source + "\" \"" + destination + "\""
        else:
            logger.error(os.path.join(git_path, destination) + " already exists.")
            sys.exit(1)
    return "git -C " + git_path + " mv \"" + source + "\" \"" + destination + "\""


def build_commit_cmd(source, destination, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'move \"" + source +
            "\" to \"" + destination + "\"\'"]


def mv(args):
    for source in args.source:
        # set all paths
        git_path = get_git_root(os.path.dirname(args.destination))
        source_filename = os.path.join(os.getcwd(), source)
        destination_filename = os.path.join(os.getcwd(), args.destination)
        if not os.path.exists(source_filename):
            source_filename = os.path.join(git_path, source)
            destination_filename = os.path.join(git_path, args.destination)
        if not os.path.exists(source_filename):
            logger.error(source + " does not exist.")
            sys.exit(1)
        if os.path.isdir(destination_filename) and not os.path.isdir(source_filename):
            destination_filename = os.path.join(destination_filename, os.path.basename(source_filename))

        destination_filename = os.path.relpath(destination_filename, git_path)
        source_filename = os.path.relpath(source_filename, git_path)
        # build commands
        mv_cmd = build_mv_cmd(git_path, source_filename, destination_filename, args.force, args.rename)
        [commit_cmd, commit_msg] = build_commit_cmd(source_filename,
                                                    destination_filename,
                                                    git_path)

        # run commands
        run_cmd(mv_cmd)
        run_cmd(commit_cmd, commit_msg)
