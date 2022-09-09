#!/usr/bin/env python3

import logging
import os
import sys
import glob

from onyo.utils import (
    build_git_add_cmd,
    is_git_dir,
    get_git_root,
    run_cmd
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(directory):
    return ["git -C \"" + directory + "\" commit -m", "initialize onyo repository."]


def build_git_init_cmd(directory):
    if is_git_dir(directory) and os.path.isdir(directory + "/.onyo"):
        logger.error(directory + " has already a onyo configuration directory and is a git repository.")
        sys.exit(1)
    elif is_git_dir(directory):
        logger.info(directory + " is already a  git repository.")
        return None
    return "git -C \"" + directory + "\"" + " init --initial-branch=master "


def build_onyo_init_cmd(directory):
    if os.path.isdir(os.path.join(directory + "/.onyo")) and not os.path.isdir(os.path.join(directory + "/.git")):
        logger.error(directory + " has an onyo configuration directory, but " +
                     "is not a git repository. Either delete the onyo " +
                     "configuration directory or use git init to manually " +
                     "initialize as git repository.")
        sys.exit(1)
    elif os.path.isdir(os.path.join(directory + "/.onyo")):
        logger.error(directory + " has already an onyo configuration directory.")
        sys.exit(1)
    return "mkdir \"" + os.path.join(directory + "/.onyo") + "\" \"" + os.path.join(directory + "/.onyo/temp") + "\" \"" + os.path.join(directory, ".onyo/templates/") + "\" \"" + os.path.join(directory, ".onyo/validation/") + "\""


def create_file_cmd(directory):
    return "touch \"" + os.path.join(directory + "/.onyo/.anchor") + "\" \"" + os.path.join(directory + "/.onyo/temp/.anchor") + "\" \"" + os.path.join(directory + "/.onyo/templates/.anchor") + "\" \"" + os.path.join(directory, ".onyo/validation/.anchor") + "\""


def prepare_arguments(directory, onyo_root):
    if directory is None:
        directory = onyo_root
    else:
        directory = os.path.join(onyo_root, directory)
    if not os.path.isdir(directory):
        logger.error("\"" + directory + "\" is no existing directory.")
        sys.exit(1)
    return directory


def init(args, onyo_root):
    """
    Initialize an Onyo repository. The directory will be initialized as a git
    repository (if it is not one already), the .onyo/ directory created
    (containing default config files, templates, etc), and everything committed.

    The current working directory will be initialized if neither ``directory``
    nor the ``onyo -C <dir>`` option are specified.

    Running ``onyo init`` on an existing repository is safe. It will not
    overwrite anything; it will exit with an error.
    """

    # set and check path
    directory = prepare_arguments(args.directory, onyo_root)
    # build commands
    git_init_command = build_git_init_cmd(directory)
    onyo_init_command = build_onyo_init_cmd(directory)
    create_file_command = create_file_cmd(directory)
    git_add_command = build_git_add_cmd(directory, ".onyo/")
    [commit_cmd, commit_msg] = build_commit_cmd(directory)
    template_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../templates/")
    validation_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../validation/")
    # run commands
    if git_init_command is not None:
        run_cmd(git_init_command)
    run_cmd(onyo_init_command)
    run_cmd(create_file_command)
    os.chdir(directory)
    os.system("onyo config history.interactive \\\"tig --follow\\\"")
    os.system("onyo config history.non-interactive \\\"git --no-pager log --follow\\\"")
    os.system("onyo config template.default standard")
    run_cmd("cp -R \"" + "\" \"".join(glob.glob(os.path.join(template_path, "*"), recursive=True)) + "\" \"" + os.path.join(directory, ".onyo/templates/") + "\"")
    run_cmd("cp -R \"" + "\" \"".join(glob.glob(os.path.join(validation_path, "*"), recursive=True)) + "\" \"" + os.path.join(directory, ".onyo/validation/") + "\"")
    run_cmd(git_add_command)
    run_cmd(commit_cmd, commit_msg)
    logger.info(commit_msg + ": " + get_git_root(directory))
