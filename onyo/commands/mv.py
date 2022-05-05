#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    run_cmd
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_mv_cmd(onyo_root, source, destination, force, rename):
    if (os.path.basename(destination) != os.path.basename(source) and not
            (rename or os.path.isdir(source))):
        return (os.path.basename(source) + " -> " + os.path.basename(destination) + " Assets can't be renamed without --rename.")
    if os.path.isfile(os.path.join(onyo_root, destination)):
        if force:
            return "git -C " + onyo_root + " mv -f \"" + source + "\" \"" + destination + "\""
        else:
            return (os.path.join(onyo_root, destination) + " already exists.")
    return "git -C " + onyo_root + " mv \"" + source + "\" \"" + destination + "\""


def build_commit_cmd(list_of_commands, onyo_root):
    return ["git -C " + onyo_root + " commit -m", "move asset(s).\n\n" + "\n".join(list_of_commands)]


def prepare_arguments(sources, destination, force, rename, onyo_root):
    problem_str = ""
    list_of_commands = []
    list_of_destinations = []
    for source in sources:
        # set all paths
        source_filename = os.path.join(onyo_root, source)
        destination_filename = os.path.join(onyo_root, destination)
        if not os.path.exists(source_filename):
            problem_str = problem_str + "\n" + source + " does not exist."
        if os.path.isdir(destination_filename) and not os.path.isdir(source_filename):
            destination_filename = os.path.join(destination_filename, os.path.basename(source_filename))
        destination_filename = os.path.relpath(destination_filename, onyo_root)
        source_filename = os.path.relpath(source_filename, onyo_root)
        # build commands
        current_cmd = build_mv_cmd(onyo_root, source_filename, destination_filename, force, rename)
        if destination_filename in list_of_destinations:
            problem_str = problem_str + "\n" + "Can't move multiple assets to " + destination_filename
        list_of_destinations.append(destination_filename)
        if "git -C" in current_cmd:
            list_of_commands.append(current_cmd)
        else:
            problem_str = problem_str + "\n" + current_cmd
    if problem_str != "":
        logger.error(problem_str + "\nNo folders or assets moved.")
        sys.exit(1)
    return list_of_commands


def mv(args, onyo_root):
    # check and set paths
    list_of_commands = prepare_arguments(args.source, args.destination, args.force, args.rename, onyo_root)
    # run list of commands, afterwards commit
    for command in list_of_commands:
        run_cmd(command)
    [commit_cmd, commit_msg] = build_commit_cmd(list_of_commands, onyo_root)
    run_cmd(commit_cmd, commit_msg)
