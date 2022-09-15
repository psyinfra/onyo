#!/usr/bin/env python3

import logging
import os
import sys
from pathlib import Path
from git import Repo
from onyo.commands.fsck import fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def run_mkdir(onyo_root, new_dir, repo):
    """
    Recursively create a directory containing an .anchor file. Stage (but do not
    commit) the .anchor file.

    Returns True on success.
    """
    full_dir = os.path.join(onyo_root, new_dir)

    # make the full path
    Path(full_dir).mkdir(parents=True, exist_ok=True)

    # create the anchor files and add to git
    loop_dir = onyo_root
    for d in new_dir.split(os.path.sep):
        loop_dir = os.path.join(loop_dir, d)
        anchor_file = os.path.join(loop_dir, '.anchor')

        Path(anchor_file).touch(exist_ok=True)
        repo.git.add(anchor_file)

    return True


def sanitize_dirs(directories, onyo_root):
    """
    Check and normalize a list of directories. If any exist, print and error.

    Returns a list of normed directories on success.
    """
    dirs_to_create = []
    dirs_exist = []

    for d in directories:
        # TODO: ideally, this would return a list of normed paths, relative to
        # the root of the onyo repository (not to be confused with onyo_root).
        # This would allow commit messages that are consistent regardless of
        # where onyo is invoked from.
        norm_dir = os.path.normpath(d)
        full_dir = os.path.join(onyo_root, norm_dir)

        # check if it exists
        if os.path.isdir(full_dir):
            dirs_exist.append(d)
            continue

        dirs_to_create.append(norm_dir)

    # exit
    if dirs_exist:
        logger.error("No directories created. The following already exist:")
        logger.error('\n'.join(dirs_exist))
        sys.exit(1)

    return dirs_to_create


def mkdir(args, onyo_root):
    """
    Create ``directory``\(s). Intermediate directories will be created as needed
    (i.e. parent and child directories can be created in one call).

    Onyo creates an empty ``.anchor`` file in directories, to force git to track
    directories even when they are empty.

    If the directory already exists, Onyo will throw an error. When multiple
    directories are passed to Onyo, all will be checked before attempting to
    create them.
    """
    repo = Repo(onyo_root)
    fsck(args, onyo_root, quiet=True)

    dir_list = sanitize_dirs(args.directory, onyo_root)
    for d in dir_list:
        run_mkdir(onyo_root, d, repo)

    repo.git.commit(m='new directory(s): ' + ', '.join(dir_list))
