#!/usr/bin/env python3

import logging
import os

from onyo.utils import run_cmd

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_cat_cmd(file):
    this_asset = file
    onyo_repository_dir = os.environ.get('ONYO_REPOSITORY_DIR')
    if not os.path.isfile(this_asset) and onyo_repository_dir is not None:
        this_asset = os.path.join(onyo_repository_dir, this_asset)
    if not os.path.isfile(this_asset):
        logger.warning(file + " does not exist.")
        return None
    return "cat \"" + this_asset + "\""


def cat(args):
    for file in args.file:
        # build command
        cat_command = build_cat_cmd(file)

        # run commands
        if cat_command is not None:
            output = run_cmd(cat_command)
            print(output.strip())
