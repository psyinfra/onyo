import logging
import os
import sys

from onyo.lib import Repo, InvalidOnyoRepoError
from onyo.utils import (
    run_cmd,
    edit_file
)

logging.basicConfig()
log = logging.getLogger('onyo')


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
        log.error(problem_str)
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
    try:
        repo = Repo(onyo_root)
        # "onyo fsck" is intentionally not run here.
        # This is so "onyo edit" can be used to fix an existing problem. This has
        # benefits over just simply using `vim`, etc directly, as "onyo edit" will
        # validate the contents of the file before saving and committing.
    except InvalidOnyoRepoError:
        sys.exit(1)

    # check and set paths
    list_of_sources = prepare_arguments(args.asset, onyo_root)
    # iterate over file list, edit them, add changes
    for source in list_of_sources:
        git_filepath = os.path.relpath(source, onyo_root)
        # change file
        edit_file(source, onyo_root)
        # add any changes
        repo._git(['add', git_filepath])

    # commit changes
    files_staged = repo.files_staged
    if files_staged:
        repo._git(['commit', '-m', 'edit asset(s).\n\n' + '\n'.join(files_staged)])
