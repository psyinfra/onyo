import logging
import subprocess
import sys
from pathlib import Path

from onyo import Repo, OnyoInvalidRepoError

logging.basicConfig()
log = logging.getLogger('onyo')


def sanitize_directories(repo: Repo, directories: list[str]) -> list[str]:
    """
    Check a list of directories. If any do not exist or are a file, and error
    will be printed.

    Returns a string of the valid directories relative to opdir.
    """
    dirs = []
    error_path_not_in_repo = []
    error_path_not_dir = []

    for d in directories:
        full_path = Path(repo.opdir, d).resolve()
        if not full_path.is_relative_to(repo.root):
            error_path_not_in_repo.append(d)
            continue

        if full_path.is_dir():
            dirs.append(full_path.relative_to(repo.opdir))
        else:
            error_path_not_dir.append(d)

    if error_path_not_in_repo or error_path_not_dir:
        print("All paths must be directories inside the repository.",
              file=sys.stderr)
        if error_path_not_in_repo:
            print('The following paths are not inside the repository:\n' +
                  repo._n_join(error_path_not_in_repo), file=sys.stderr)
        if error_path_not_dir:
            print('The following paths are not directories:\n' +
                  repo._n_join(error_path_not_dir), file=sys.stderr)
        sys.exit(1)

    return dirs


def tree(args, opdir: str) -> None:
    """
    List the assets and directories in ``directory`` using ``tree``.
    """
    repo = None
    try:
        repo = Repo(opdir)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    # sanitize the paths
    dirs = sanitize_directories(repo, args.directory)

    # run it
    ret = subprocess.run(['tree'] + dirs, capture_output=True, text=True)

    # check for errors
    if ret.stderr:
        print(ret.stderr)
        sys.exit(1)

    # print tree output
    print(ret.stdout)
