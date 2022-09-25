#!/usr/bin/env python3

import logging
import os
import sys

from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def sanitize_paths(paths, onyo_root):
    """
    Check and normalize a list of paths. If paths do not exist or are not files,
    print paths and exit with error.
    """
    paths_to_cat = []
    error_path_absent = []
    error_path_not_file = []

    for p in paths:
        # Returns a set of normalized paths relative to onyo_root
        norm_path = os.path.normpath(p)
        # TODO: This is wrong when an absolute path is provided
        full_path = os.path.join(onyo_root, norm_path)

        # path must exist
        if not os.path.exists(full_path):
            error_path_absent.append(p)
            continue

        # path must be a file
        if not os.path.isfile(full_path):
            error_path_not_file.append(p)
            continue

        paths_to_cat.append(full_path)

    if error_path_absent:
        logger.error("The following paths do not exist:")
        logger.error("\n".join(error_path_absent))
        logger.error("\n Exiting.")
        sys.exit(1)

    if error_path_not_file:
        logger.error("The following paths are not files:")
        logger.error("\n".join(error_path_not_file))
        logger.error("\n Exiting.")
        sys.exit(1)

    return paths_to_cat


def cat(args, onyo_root):
    """
    Print the contents of ``asset``\(s) to the terminal without parsing or
    validating the contents.
    """
    # run onyo fsck for read only commands
    read_only_fsck(args, onyo_root, quiet=True)

    paths_to_cat = sanitize_paths(args.asset, onyo_root)

    # open file and print to stdout
    for path in paths_to_cat:
        with open(path, 'r') as fin:
            print(fin.read(), end="")
