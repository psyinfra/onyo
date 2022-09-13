#!/usr/bin/env python3

import logging
import os
import sys

from onyo.utils import (
    build_git_add_cmd,
    run_cmd
)
from onyo.commands.fsck import fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(sources, onyo_root):
    return ["git -C \"" + onyo_root + "\" commit -m", "deleted asset(s).\n\n" + "\n".join(sources)]


def run_rm(onyo_root, source):
    full_path = os.path.join(onyo_root, source)
    # run the rm commands
    run_cmd("rm -rdf \"" + full_path + "\"")
    # git add
    git_add_cmd = build_git_add_cmd(onyo_root, source)
    run_cmd(git_add_cmd)
    return full_path


def prepare_arguments(sources, quiet, yes, onyo_root):
    problem_str = ""
    list_of_sources = []
    # check flags
    if quiet and not yes:
        problem_str = problem_str + "\nonyo rm --quiet can't be run without --yes flag."
    # check sources
    for source in sources:
        current_source = os.path.join(onyo_root, source)
        if not os.path.exists(current_source):
            problem_str = problem_str + "\n" + current_source + " does not exist."
        else:
            list_of_sources.append(current_source)
    if problem_str != "":
        logger.error(problem_str + "\nNo folders or assets deleted.")
        sys.exit(1)
    return list(dict.fromkeys(list_of_sources))


def rm(args, onyo_root):
    """
    Delete the ``asset``\(s) and ``directory``\(s).

    Onyo will present a complete list of all files and folders to delete, and
    prompt the user for confirmation.

    - ``--quiet``: Silence the output (requires the ``--yes`` flag)
    - ``--yes``: Respond "yes" to the prompt and run non-interactively
    """

    # run onyo fsck
    fsck(args, onyo_root, quiet=True)
    # needs to check onyo root or rel path, also if in git
    list_of_sources = prepare_arguments(args.path, args.quiet, args.yes, onyo_root)

    if not args.quiet:
        print("onyo wants to delete:")
        print("\n".join(list_of_sources))
    if not args.yes:
        delete_input = str(input("Delete assets? (y/N) "))
        if delete_input not in ['y', 'Y', 'yes']:
            logger.info("Nothing deleted.")
            sys.exit(0)

    # build commit command and message
    [commit_cmd, commit_msg] = build_commit_cmd(list_of_sources, onyo_root)

    for source in list_of_sources:
        # if stopped existing since prepare_arguments(), it was deleted
        # with the loop before
        if not os.path.exists(source):
            continue
        # set paths
        run_rm(onyo_root, source)
    # run commit command
    run_cmd(commit_cmd, commit_msg)
