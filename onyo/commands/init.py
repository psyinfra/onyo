#!/usr/bin/env python3

import logging
import os
import sys
import shutil
from pathlib import Path
import git

logging.basicConfig()
logger = logging.getLogger('onyo')


def get_skel_dir():
    """
    Return the path of the skel/ dir in the onyo module directory.
    """
    onyo_module_dir = Path(__file__).resolve().parent.parent
    skel = os.path.join(onyo_module_dir, 'skel/')
    return skel


def sanitize_dir(directory, onyo_root):
    """
    Check the directory for viability as an init target.

    Returns a normed directory on success.
    """
    if directory:
        norm_dir = os.path.normpath(directory)
        full_dir = os.path.join(onyo_root, norm_dir)
    else:
        norm_dir = os.path.normpath(onyo_root)
        full_dir = norm_dir

    # sanity checks
    # already an .onyo repo
    dot_onyo = os.path.join(full_dir, ".onyo")
    if os.path.isdir(dot_onyo):
        logger.error(dot_onyo + " already exists. Exiting.")
        sys.exit(1)

    # target is a file, etc
    if os.path.exists(full_dir) and not os.path.isdir(full_dir):
        logger.error(full_dir + " exists but is not a directory. Exiting.")
        sys.exit(1)

    # make sure parent exists
    if not os.path.isdir(full_dir):
        parent_dir = os.path.dirname(full_dir)
        if not os.path.isdir(parent_dir):
            logger.error(parent_dir + " does not exist. Exiting.")
            sys.exit(1)

    return norm_dir


def init(args, onyo_root):
    """
    Initialize an Onyo repository. The directory will be initialized as a git
    repository (if it is not one already), the ``.onyo/`` directory created
    (containing default config files, templates, etc), and everything committed.

    The current working directory will be initialized if neither ``directory``
    nor the ``onyo -C <dir>`` option are specified.

    Running ``onyo init`` on an existing repository is safe. It will not
    overwrite anything; it will exit with an error.
    """
    target_dir = sanitize_dir(args.directory, onyo_root)
    Path(target_dir).mkdir(exist_ok=True)

    try:
        repo = git.Repo(target_dir)
        logger.info(target_dir + " has a git repository.")
    except git.exc.InvalidGitRepositoryError:
        repo = git.Repo.init(target_dir)

    # populate .onyo dir
    skel = get_skel_dir()
    dot_onyo = os.path.join(target_dir, ".onyo")
    shutil.copytree(skel, dot_onyo)

    # add and commit
    repo.git.add('.onyo/')
    repo.git.commit(m='initialize onyo repository')

    # print success
    abs_dot_onyo = str(os.path.abspath(dot_onyo))
    print(f'Initialized Onyo repository in {abs_dot_onyo}')
