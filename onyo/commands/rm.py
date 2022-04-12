#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    build_git_add_cmd,
    get_git_root,
    get_full_filepath,
    run_cmd
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(sources, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'deleted assets.\'"]


def run_rm(git_directory, source):
    full_path = os.path.join(git_directory, source)
    # run the rm commands
    run_cmd("rm -rdf \"" + full_path + "\"")
    # git add
    git_add_cmd = build_git_add_cmd(git_directory, source)
    run_cmd(git_add_cmd)
    return full_path


def check_sources(sources):
    problem_str = ""
    list_of_sources = []
    for source in sources:
        test_git = get_git_root(source)
        current_source = get_full_filepath(test_git, source)
        if not os.path.exists(current_source):
            problem_str = problem_str + "\n" + current_source + " does not exist."
        else:
            list_of_sources.append(current_source)
    if problem_str != "":
        logger.error(problem_str + "\nNo folders or assets deleted.")
        sys.exit(1)
    return list(dict.fromkeys(list_of_sources))


def rm(args):
    # check flags
    if args.quiet and not args.yes:
        logger.error("onyo rm --quiet can't be run without --yes flag.")
        sys.exit(1)

    # needs to check onyo root or rel path, also if in git
    list_of_sources = check_sources(args.source)

    if not args.quiet:
        print("onyo wants to delete:")
        print("\n".join(list_of_sources))
    if not args.yes:
        delete_input = str(input("Delete assets? (y/n)"))
        if not delete_input == "y":
            logger.info("Nothing deleted.")
            sys.exit(0)

    # build commit command and message
    [commit_cmd, commit_msg] = build_commit_cmd(args.source[0], get_git_root(args.source[0]))

    for source in list_of_sources:
        # if stopped existing since check_sources(), it was deleted
        # with the loop before
        if not os.path.exists(source):
            continue
        # set paths
        git_directory = get_git_root(source)
        current_source = get_full_filepath(git_directory, source)
        git_folder_path = os.path.relpath(current_source, git_directory)
        run_rm(git_directory, git_folder_path)

    # run commit command
    run_cmd(commit_cmd, commit_msg)
