import logging
import sys
from pathlib import Path, PurePath

from onyo.lib import Repo, OnyoInvalidRepoError
from onyo.utils import is_protected_path

logging.basicConfig()
log = logging.getLogger('onyo')


def run_mkdir(onyo_root, new_dir, repo):
    """
    Recursively create a directory containing an .anchor file. Stage (but do not
    commit) the .anchor file.

    Returns True on success.
    """
    # create the full path tree
    Path(onyo_root, new_dir).mkdir(parents=True, exist_ok=True)

    # create the anchor files and add to git
    loop_dir = onyo_root
    for d in PurePath(new_dir).parts:
        loop_dir = Path(loop_dir, d)
        anchor_file = Path(loop_dir, '.anchor')

        anchor_file.touch(exist_ok=True)
        repo._git(['add', anchor_file.resolve()])

    return True


def sanitize_dirs(directories, onyo_root):
    """
    Check and normalize a list of directories. If any exist, print and error.

    Returns a list of normed directories on success.
    """
    dirs_to_create = []
    error_exist = []
    error_path_protected = []

    for d in directories:
        full_dir = Path(onyo_root, d).resolve()

        # check if it exists
        if full_dir.exists():
            error_exist.append(d)
            continue

        # protected paths
        if is_protected_path(full_dir):
            error_path_protected.append(d)
            continue

        # TODO: ideally, this would return a list of normed paths, relative to
        # the root of the onyo repository (not to be confused with onyo_root).
        # This would allow commit messages that are consistent regardless of
        # where onyo is invoked from.
        norm_dir = str(full_dir.relative_to(onyo_root))
        dirs_to_create.append(norm_dir)

    # exit
    if error_exist:
        log.error("No directories created. The following already exist:")
        log.error('\n'.join(error_exist))
        sys.exit(1)

    if error_path_protected:
        log.error("The following paths are protected by onyo:")
        log.error('\n'.join(error_path_protected))
        log.error("\nExiting. No directories were created.")
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
    try:
        repo = Repo(onyo_root)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    dir_list = sanitize_dirs(args.directory, onyo_root)
    for d in dir_list:
        run_mkdir(onyo_root, d, repo)

    repo._git(['commit', '-m', 'new directory(s): ' + ', '.join(dir_list)])
