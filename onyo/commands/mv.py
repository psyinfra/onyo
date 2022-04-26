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
        return (os.path.basename(source) + " -> " + os.path.basename(destination) + " Assets can't be renamed without --rename.")
    if os.path.isfile(os.path.join(git_path, destination)):
        if force:
            return "git -C " + git_path + " mv -f \"" + source + "\" \"" + destination + "\""
        else:
            return (os.path.join(git_path, destination) + " already exists.")
    return "git -C " + git_path + " mv \"" + source + "\" \"" + destination + "\""


def build_commit_cmd(list_of_commands, git_directory):
    return ["git -C " + git_directory + " commit -m", "move assets.\n" + "\n".join(list_of_commands)]


def check_sources(sources, destination, force, rename):
    problem_str = ""
    list_of_commands = []
    list_of_destinations = []
    for source in sources:
        # set all paths
        git_path = get_git_root(os.path.dirname(destination))
        source_filename = os.path.join(os.getcwd(), source)
        destination_filename = os.path.join(os.getcwd(), destination)
        # if source not reached from current directory, try from environmental
        if not os.path.exists(source_filename):
            source_filename = os.path.join(git_path, source)
            destination_filename = os.path.join(git_path, destination)
        if not os.path.exists(source_filename):
            problem_str = problem_str + "\n" + source + " does not exist."
        if os.path.isdir(destination_filename) and not os.path.isdir(source_filename):
            destination_filename = os.path.join(destination_filename, os.path.basename(source_filename))
        destination_filename = os.path.relpath(destination_filename, git_path)
        source_filename = os.path.relpath(source_filename, git_path)
        # build commands
        current_cmd = build_mv_cmd(git_path, source_filename, destination_filename, force, rename)
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


def mv(args):
    # check and set paths
    git_path = get_git_root(os.path.dirname(args.destination))
    list_of_commands = check_sources(args.source, args.destination, args.force, args.rename)
    # run list of commands, afterwards commit
    for command in list_of_commands:
        run_cmd(command)
    [commit_cmd, commit_msg] = build_commit_cmd(list_of_commands, git_path)
    run_cmd(commit_cmd, commit_msg)
