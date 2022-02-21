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
        logger.info(run_output)

def build_tree_cmd(directory):
    if not os.path.isdir(directory):
        logger.error(directory + " does not exist.")
        sys.exit(0)
    return "tree " + directory


def tree(args):
    # build commands
    tree_command = build_tree_cmd(args.directory)

    # run commands
    run_cmd(tree_command)
