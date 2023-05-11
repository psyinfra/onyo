from __future__ import annotations
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import Repo, OnyoInvalidRepoError

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')


def sanitize_directories(repo: Repo, directories: list[str]) -> list[Path]:
    """
    Check a list of directories. If any do not exist or are a file, and error
    will be printed.

    Returns a string of the valid directories.
    """
    dirs = []
    error_path_not_in_repo = []
    error_path_not_dir = []

    for d in directories:
        full_path = Path(d).resolve()

        if full_path.is_dir():
            try:
                dirs.append(full_path.relative_to(repo.root))
            except ValueError:
                error_path_not_in_repo.append(d)
                continue
        else:
            error_path_not_dir.append(d)

    if error_path_not_in_repo or error_path_not_dir:
        print(
            'All paths must be directories inside the repository.',
            file=sys.stderr)

        if error_path_not_in_repo:
            print(
                'The following paths are not inside the repository: ',
                *map(str, error_path_not_in_repo), sep='\n', file=sys.stderr)

        if error_path_not_dir:
            print(
                'The following paths are not directories:',
                *map(str, error_path_not_dir), sep='\n', file=sys.stderr)

        sys.exit(1)

    return dirs


def tree(args: argparse.Namespace) -> None:
    """
    List the assets and directories in ``directory`` using ``tree``.
    """
    repo = None
    try:
        repo = Repo(Path.cwd(), find_root=True)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    # sanitize the paths
    dirs = sanitize_directories(repo, args.directory)

    # run it
    ret = subprocess.run(
        ['tree', *map(str, dirs)], capture_output=True, text=True)

    # check for errors
    if ret.stderr:
        print(ret.stderr)
        sys.exit(1)

    # print tree output
    print(ret.stdout)
