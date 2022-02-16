#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

logging.basicConfig()
logger = logging.getLogger('onyo mv')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Frying Onyo'
    )
    parser.add_argument(
        '-f', '--force',
        required=False,
        default=False,
        action='store_true',
        help='Forcing to move file'
    )
    parser.add_argument(
        '-r', '--rename',
        required=False,
        default=False,
        action='store_true',
        help='Rename file'
    )
    parser.add_argument(
        'source',
        metavar='source',
        help='Source file'
    )
    parser.add_argument(
        'destination',
        metavar='destination',
        help='Destination file'
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


def build_mv_cmd(source, destination, force, rename):
    if not os.path.exists(source):
        logger.warning("err: " + source + " does not exist.")
        sys.exit(0)
    # to look at destination path/file separately
    if os.path.isdir(destination):
        destination_path = destination
        destination_filename = os.path.basename(source)
    elif os.path.isdir(destination.replace(os.path.basename(destination), "")):
        destination_path = destination.replace(os.path.basename(destination), "")
        destination_filename = os.path.basename(destination)
    # should check if folder exists. Is os.path.exists() the better function?
    if not os.path.isdir(destination_path):
        logger.warning("err: " + destination_path + " does not exist.")
        sys.exit(0)
    if destination_filename != os.path.basename(source) and rename == False:
        logger.warning("err: " + destination_path + "/" + destination_filename +
                " no renaming allowed.")
        sys.exit(0)
    if os.path.isfile(destination_path + "/" + destination_filename):
        if force == True:
            return "git mv -f " + source + " " + destination_path + "/" + destination_filename
        else:
            logger.warning("err: " + destination_path + "/" +
                    destination_filename + " already exists.")
            sys.exit(0)
    return "git mv " + source + " " + destination_path + "/" + destination_filename


def build_commit_cmd(source, destination):
    return ["git commit -m", "\'move " + source + " to " + destination + "\'"]


def main():
    args = parse_args()

    # build commands
    mv_cmd = build_mv_cmd(args.source, args.destination, args.force, args.rename)
    [commit_cmd, commit_msg] = build_commit_cmd(args.source, args.destination)

    # run commands
    run_cmd(mv_cmd)
    run_cmd(commit_cmd, commit_msg)

if __name__ == '__main__':
    main()

