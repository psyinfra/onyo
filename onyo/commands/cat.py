import logging
import sys
from pathlib import Path

from onyo import Repo, OnyoInvalidRepoError

logging.basicConfig()
log = logging.getLogger('onyo')


def sanitize_paths(paths: list[str], opdir: str) -> list[Path]:
    """
    Check and normalize a list of paths. If paths do not exist or are not files,
    print paths and exit with error.
    """
    paths_to_cat = []
    error_path_absent = []
    error_path_not_file = []

    for p in paths:
        # TODO: This is wrong when an absolute path is provided
        full_path = Path(opdir, p).resolve()

        # path must exist
        if not full_path.exists():
            error_path_absent.append(p)
            continue

        # path must be a file
        if not full_path.is_file():
            error_path_not_file.append(p)
            continue

        paths_to_cat.append(full_path)

    if error_path_absent:
        log.error("The following paths do not exist:")
        log.error("\n".join(error_path_absent))
        log.error("\n Exiting.")
        sys.exit(1)

    if error_path_not_file:
        log.error("The following paths are not files:")
        log.error("\n".join(error_path_not_file))
        log.error("\n Exiting.")
        sys.exit(1)

    return paths_to_cat


def cat(args, opdir: str) -> None:
    """
    Print the contents of ``asset``\\(s) to the terminal without parsing or
    validating the contents.
    """
    repo = None
    try:
        repo = Repo(opdir)
        repo.fsck(['asset-yaml'])
    except OnyoInvalidRepoError:
        sys.exit(1)

    paths_to_cat = sanitize_paths(args.asset, opdir)

    # open file and print to stdout
    for path in paths_to_cat:
        print(path.read_text(), end='')
