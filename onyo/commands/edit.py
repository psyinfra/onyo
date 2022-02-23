#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

from git import Repo, exc

logging.basicConfig()
logger = logging.getLogger('onyo')


def is_git_dir(directory):
    try:
        Repo(directory).git_dir
        return True
    except exc.InvalidGitRepositoryError:
        return False

def get_editor():
    editor = os.environ.get('EDITOR')
    if editor == None:
        editor = 'nano'
    return editor

def run_cmd(cmd, comment=""):
    if comment != "":
        run_process = subprocess.Popen(cmd.split() + [comment],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True)
    else:
        run_process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, universal_newlines=True)
    run_output, run_error = run_process.communicate()
    if (run_error != ""):
        logger.error(run_error)
        sys.exit(0)
    else:
        logger.info(cmd + " " + comment)
    return run_output

def build_commit_cmd(file, git_directory):
    return ["git -C "+ git_directory + " commit -m", "\'edit " + file + "\'"]


def edit_file_cmd(file):
    if not os.path.isfile(file):
        logger.error(file + " does not exist.")
        sys.exit(0)
    os.system(get_editor() + " " + file)
    return


def build_git_add_cmd(file, git_directory):
    return "git -C " + git_directory + " add " + file


def get_git_root(path):
    # first checks if file is in git from current position
    try:
        git_repo = Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        return git_root
    # otherwise checks if given file relative to $ONYO_REPOSITORY_DIR is in a
    # git repository
    except exc.NoSuchPathError:
        onyo_path = os.environ.get('ONYO_REPOSITORY_DIR')
        if onyo_path == None:
            logger.error("wrong.")
            sys.exit(0)
        git_repo = Repo(os.path.join(path, onyo_path), search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        return git_root

def get_full_filepath(git_directory, file):
    full_filepath = os.path.join(git_directory, file)
    if not os.path.isfile(full_filepath):
        full_filepath = os.path.join(git_directory, os.getcwd())
        full_filepath = os.path.join(full_filepath, file)
    if not os.path.isfile(full_filepath):
        logger.error(file + " not found.")
        sys.exit(0)
    return full_filepath

def edit(args):

    # folder that contains git, by environment var or by position of file
    git_directory = get_git_root(args.file)
    # wants to get the full filepath, and the path relative from git_directory
    full_filepath = get_full_filepath(git_directory, args.file)
    git_filepath = os.path.relpath(full_filepath, git_directory)

    # check if file is in git. There might be a better test, since this just
    # tests for "untracked", not for newest version.
    run_output = run_cmd("git -C " + git_directory + " ls-tree -r HEAD ")
    if not git_filepath in run_output:
        logger.error(git_filepath + " is not in onyo.")
        sys.exit(0)

    # change file
    edit_file_cmd(full_filepath)

    # TODO: check here if yaml still works

    # check if changes happened and add+commit them
    repo = Repo(git_directory)
    changedFiles = [ item.a_path for item in repo.index.diff(None) ]
    if len(changedFiles) != 0:
        git_add_cmd = build_git_add_cmd(git_filepath, git_directory)
        [commit_cmd, commit_msg] = build_commit_cmd(git_filepath, git_directory)

        # run commands
        run_cmd(git_add_cmd)
        run_cmd(commit_cmd, commit_msg)
    else:
        logger.error("no changes made.")
        sys.exit(0)
