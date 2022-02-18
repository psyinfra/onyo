#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

logging.basicConfig()
logger = logging.getLogger('onyo init')

def parse_args():
    parser = argparse.ArgumentParser(
        description='Frying Onyo'
    )
    parser.add_argument(
        'directory',
        metavar='directory',
        nargs='?',
        default= ".",
        help='Directory to initialize as onyo repository'
    )
    return parser.parse_args()

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

def build_commit_cmd(directory):
    return ["git commit -m", "\'initialize " + directory + " as onyo repository\'"]


def build_git_init_cmd(directory):
    if os.path.isdir(directory + "/.git"):
        logger.warning("err: " + directory + "/.git already exists.")
        sys.exit(0)
    return "git init --initial-branch=master " + directory


def build_onyo_init_cmd(directory):
    if os.path.isdir(directory + "/.onyo"):
        logger.warning("err: " + directory + "/.onyo already exists.")
        sys.exit(0)
    return "mkdir " + directory + "/.onyo"


def build_git_add_cmd(directory):
    return "git add " + directory + "/.onyo/"


def create_file_cmd(directory):
    return "touch " + directory + "/.onyo/onyo.txt"


def main():
    args = parse_args()

    # build commands
    git_init_command = build_git_init_cmd(args.directory)
    onyo_init_command = build_onyo_init_cmd(args.directory)
    create_file_command = create_file_cmd(args.directory)
    git_add_command = build_git_add_cmd(args.directory)
    [commit_cmd, commit_msg] = build_commit_cmd(args.directory)

    # run commands
    run_cmd(git_init_command)
    run_cmd(onyo_init_command)
    run_cmd(create_file_command)
    run_cmd(git_add_command)
    run_cmd(commit_cmd, commit_msg)



if __name__ == '__main__':
    main()

