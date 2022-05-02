#!/usr/bin/env python3

import logging
import os
import sys

from git import Repo

from onyo.utils import (
    build_git_add_cmd,
    get_full_filepath,
    get_git_root,
    run_cmd,
    edit_file
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(files, git_directory):
    return ["git -C \"" + git_directory + "\" commit -m", "edit files\n" + "\n".join(files)]


def prepare_arguments(sources):
    problem_str = ""
    list_of_sources = []
    if isinstance(sources, str):
        sources = ["".join(sources)]
    git_directory = get_git_root(sources[0])
    for source in sources:
        test_git = get_git_root(source)
        current_source = get_full_filepath(test_git, source)
        if git_directory != test_git:
            problem_str = problem_str + "\n" + current_source + " not in same git as " + sources[0]
        if not os.path.exists(current_source):
            problem_str = problem_str + "\n" + current_source + " does not exist."
        else:
            list_of_sources.append(current_source)
    if problem_str != "":
        logger.error(problem_str + "\nNo folders or assets moved.")
        sys.exit(1)
    return list(dict.fromkeys(list_of_sources))


def edit(args):
    # check and set paths
    list_of_sources = prepare_arguments(args.file)

    for source in list_of_sources:
        git_directory = get_git_root(source)
        git_filepath = os.path.relpath(source, git_directory)

        # check if file is in git
        run_output = run_cmd("git -C \"" + git_directory + "\" ls-tree -r HEAD ")
        if git_filepath not in run_output:
            logger.error(git_filepath + " is not in onyo.")
            sys.exit(1)

        # change file
        if not args.non_interactive:
            edit_file(source)

        # check if changes happened and add them
        repo = Repo(git_directory)
        changed_files = [item.a_path for item in repo.index.diff(None)]
        if len(changed_files) != 0:
            git_add_cmd = build_git_add_cmd(git_directory, git_filepath)
            run_cmd(git_add_cmd)

    # commit changes
    [commit_cmd, commit_msg] = build_commit_cmd(changed_files, get_git_root(list_of_sources[0]))
    run_cmd(commit_cmd, commit_msg)
