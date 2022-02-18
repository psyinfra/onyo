#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

logging.basicConfig()
logger = logging.getLogger('onyo edit')

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
        logger.warning("err: " + run_error)
        sys.exit(0)
    else:
        logger.warning("ran: " + cmd + " " + comment)

def build_commit_cmd(file):
    return ["git commit -m", "\'edit " + file + "\'"]


def edit_file_cmd(file):
    if not os.path.isfile(file):
        logger.warning("err: " + file + " does not exist.")
        sys.exit(0)
    os.system(os.environ.get('EDITOR') + " " + file)
    return


def build_git_add_cmd(file):
    return "git add " + file


def edit(args):
    # build commands
    edit_file_cmd(args.file)
    git_add_cmd = build_git_add_cmd(args.file)
    [commit_cmd, commit_msg] = build_commit_cmd(args.file)

    # run commands
    run_cmd(git_add_cmd)
    run_cmd(commit_cmd, commit_msg)
