import logging
import os
import sys

from git import Repo

from onyo.utils import (
    build_git_add_cmd,
    run_cmd,
    edit_file
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(files, onyo_root):
    return ["git -C \"" + onyo_root + "\" commit -m", "edit asset(s).\n\n" + "\n".join(files)]


def prepare_arguments(sources, onyo_root):
    problem_str = ""
    list_of_sources = []
    if isinstance(sources, str):
        sources = ["".join(sources)]
    for source in sources:
        current_source = source
        if not os.path.isfile(current_source):
            current_source = os.path.join(onyo_root, source)
        if not os.path.exists(current_source):
            problem_str = problem_str + "\n" + current_source + " does not exist."
        # check if file is in git
        run_output = run_cmd("git -C \"" + onyo_root + "\" ls-tree -r HEAD ")
        if source not in run_output:
            problem_str = problem_str + "\n" + current_source + " is not in onyo."
        else:
            list_of_sources.append(current_source)
    if problem_str != "":
        logger.error(problem_str)
        sys.exit(1)
    return list(dict.fromkeys(list_of_sources))


def edit(args, onyo_root):
    """
    Open the ``asset`` file(s) using the editor specified by "onyo.core.editor",
    the environment variable ``EDITOR``, or ``nano`` (as a final fallback).

    When multiple asset files are given, Onyo will open them in sequence.

    After editing an ``asset``, the contents will be checked for valid YAML and
    also against any matching rules in ``.onyo/validation/validation.yaml``. If
    problems are found, the choice will be offered to reopen the editor to fix
    them, or abort and return to the original state.
    """
    # "onyo fsck" is intentionally not run here.
    # This is so "onyo edit" can be used to fix an existing problem. This has
    # benefits over just simply using `vim`, etc directly, as "onyo edit" will
    # validate the contents of the file before saving and committing.

    # check and set paths
    list_of_sources = prepare_arguments(args.asset, onyo_root)
    # iterate over file list, edit them, add changes
    for source in list_of_sources:
        git_filepath = os.path.relpath(source, onyo_root)
        # change file
        edit_file(source, onyo_root)
        # check if changes happened and add them
        repo = Repo(onyo_root)
        changed_files = [item.a_path for item in repo.index.diff(None)]
        if len(changed_files) != 0:
            git_add_cmd = build_git_add_cmd(onyo_root, git_filepath)
            run_cmd(git_add_cmd)
    # commit changes
    [commit_cmd, commit_msg] = build_commit_cmd(changed_files, onyo_root)
    run_cmd(commit_cmd, commit_msg)
