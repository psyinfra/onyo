#!/usr/bin/env python3

import subprocess
import logging
import os
import sys
import argparse

from onyo.utils import *

logging.basicConfig()
logger = logging.getLogger('onyo')
logger.setLevel(logging.INFO)

def build_mv_cmd(git_path, source_filename, destination_filename, force, rename):

    if not os.path.exists( os.path.join(git_path, source_filename)):
        logger.error(source_filename + " does not exist.")
        sys.exit(0)
    if os.path.basename(destination_filename) != os.path.basename(source_filename) and rename == False:
        logger.error( os.path.basename(destination_filename) +" -> " +  os.path.basename(source_filename) #os.path.join(git_path, destination_filename) +
                + " no renaming allowed.")
        sys.exit(0)
    if os.path.isfile(os.path.join(git_path, destination_filename)):
        if force == True:
            return "git -C " + git_path + " mv -f " + source_filename + " " + destination_filename #os.path.join(git_path, destination_filename)
        else:
            logger.error(os.path.join(git_path, destination_filename) + " already exists.")
            sys.exit(0)
    return "git -C " + git_path + " mv " + source_filename + " " + destination_filename


def build_commit_cmd(source, destination, git_directory):
    return ["git -C " + git_directory + " commit -m", "\'move " + source + " to " + destination + "\'"]


def mv(args):

    for source in args.source:
        # set all paths
        git_path = get_git_root(os.path.dirname(args.destination))
        source_filename = os.path.join(os.getcwd(), source)
        destination_filename = os.path.join(os.getcwd(), args.destination)
        if not os.path.isfile(source_filename):
            source_filename = os.path.join(git_path, source)
            destination_filename = os.path.join(git_path, args.destination)
        if not os.path.isfile(source_filename):
            logger.error(source + " does not exist. :(")
            sys.exit(0)
        if not os.path.isdir(os.path.dirname(destination_filename)):
            logger.error(source + " does not exist. :(")
            system.exit(0)
        # if it is just directory, but not file, add filename
        if os.path.isdir(destination_filename):
            destination_filename = os.path.join(destination_filename, os.path.basename(source_filename))

        destination_filename = os.path.relpath(destination_filename, git_path)
        source_filename = os.path.relpath(source_filename, git_path)

        # build commands
        mv_cmd = build_mv_cmd(git_path, source_filename, destination_filename, args.force, args.rename)
        [commit_cmd, commit_msg] = build_commit_cmd(source_filename,
                destination_filename, git_path)

        # run commands
        run_cmd(mv_cmd)
        run_cmd(commit_cmd, commit_msg)
