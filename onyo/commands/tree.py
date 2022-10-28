import logging
import os
import sys
from pathlib import Path

from onyo.lib import Repo, OnyoInvalidRepoError

logging.basicConfig()
log = logging.getLogger('onyo')


def sanitize_directories(directories: list, opdir: str) -> str:
    """
    Check a list of directories. If any do not exist or are a file, and error
    will be printed.

    Returns a string of the valid directories relative to opdir.
    """
    dirs = []
    error_path = []

    for d in directories:
        full_path = Path(opdir, d)

        if full_path.is_dir():
            dirs.append(full_path.relative_to(opdir))
        else:
            error_path.append(d)

    if error_path:
        print('The following paths are not directories:\n' + '\n'.join(error_path),
              file=sys.stderr)
        sys.exit(1)

    return ' '.join(str(x) for x in dirs)


def tree(args, opdir: str) -> None:
    """
    List the assets and directories in ``directory`` using ``tree``.
    """
    try:
        repo = Repo(opdir)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    # sanitize the paths
    dirs = sanitize_directories(args.directory, opdir)

    # run it
    status = int()
    orig_cwd = os.getcwd()
    try:
        os.chdir(opdir)
        status = os.system(f"tree {dirs}")
    except:  # noqa: E722
        pass
    finally:
        os.chdir(orig_cwd)

    # covert the return status into a return code
    returncode = os.waitstatus_to_exitcode(status)

    # bubble up error retval
    if returncode != 0:
        exit(returncode)
