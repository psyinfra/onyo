#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

logging.basicConfig()
logger = logging.getLogger('onyo')

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


def build_mv_cmd(source, destination, force, rename):
    if not os.path.exists(source):
        logger.error(source + " does not exist.")
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
        logger.error(destination_path + " does not exist.")
        sys.exit(0)
    if destination_filename != os.path.basename(source) and rename == False:
        logger.error(os.path.join(destination_path, destination_filename) +
                " no renaming allowed.")
        sys.exit(0)
    if os.path.isfile(os.path.join(destination_path, destination_filename)):
        if force == True:
            return "git mv -f " + source + " " + os.path.join(destination_path,
                    destination_filename)
        else:
            logger.error(os.path.join(destination_path, destination_filename) +
                    " already exists.")
            sys.exit(0)
    return "git mv " + source + " " + os.path.join(destination_path,
            destination_filename)


def build_commit_cmd(source, destination):
    return ["git commit -m", "\'move " + source + " to " + destination + "\'"]


def mv(args):

    for source in args.source:

        # build commands
        mv_cmd = build_mv_cmd(source, args.destination, args.force, args.rename)
        [commit_cmd, commit_msg] = build_commit_cmd(source, args.destination)

        # run commands
        run_cmd(mv_cmd)
        run_cmd(commit_cmd, commit_msg)
