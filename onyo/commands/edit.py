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

def build_commit_cmd(file):
    return ["git commit -m", "\'edit " + file + "\'"]


def edit_file_cmd(file):
    if not os.path.isfile(file):
        logger.error(file + " does not exist.")
        sys.exit(0)
    os.system(get_editor() + " " + file)
    return


def build_git_add_cmd(file):
    return "git add " + file


def edit(args):
    # build commands
    if not is_git_dir(args.directory):
        logger.error(args.directory + " is not onyo.")
        sys.exit(0)

    edit_file_cmd(args.file)

    # TODO: check here if yaml still works

    # check if changes happened and add+commit them
    repo = Repo(args.directory)
    changedFiles = [ item.a_path for item in repo.index.diff(None) ]
    if len(changedFiles) != 0:
        git_add_cmd = build_git_add_cmd(args.file)
        [commit_cmd, commit_msg] = build_commit_cmd(args.file)

        # run commands
        run_cmd(git_add_cmd)
        run_cmd(commit_cmd, commit_msg)
    else:
        logger.error("no changes made.")
        sys.exit(0)
