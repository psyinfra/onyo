import logging
import sys
from pathlib import Path
from git import Repo
from onyo.commands.fsck import fsck
from onyo.utils import is_protected_path

logging.basicConfig()
logger = logging.getLogger('onyo')


def sanitize_paths(paths, onyo_root):
    """
    Check and normalize a list of paths. If any do not exist, or are protected
    paths (.anchor, .git, .onyo), then they will be printed and exit with error.

    Returns a list of normed paths on success.
    """
    paths_to_rm = []
    error_path_absent = []
    error_path_protected = []

    for p in paths:
        full_path = Path(onyo_root, p).resolve()

        # paths must exist
        if not full_path.exists():
            error_path_absent.append(p)
            continue

        # protected paths
        if is_protected_path(full_path):
            error_path_protected.append(p)
            continue

        # TODO: ideally, this would return a list of normed paths, relative to
        # the root of the onyo repository (not to be confused with onyo_root).
        # This would allow commit messages that are consistent regardless of
        # where onyo is invoked from.
        norm_path = str(full_path.relative_to(onyo_root))
        paths_to_rm.append(norm_path)

    if error_path_absent:
        logger.error("The following paths do not exist:")
        logger.error('\n'.join(error_path_absent))
        logger.error("\nExiting. Nothing was deleted.")
        sys.exit(1)

    if error_path_protected:
        logger.error("The following paths are protected by onyo:")
        logger.error('\n'.join(error_path_protected))
        logger.error("\nExiting. Nothing was deleted.")
        sys.exit(1)

    return paths_to_rm


def rm(args, onyo_root):
    """
    Delete ``asset``\(s) and ``directory``\(s).

    A complete list of all files and directories to delete will be presented
    first, and the user prompted for confirmation.
    """
    # check flags
    if args.quiet and not args.yes:
        logger.error("The --quiet flag requires --yes.")
        sys.exit(1)

    repo = Repo(onyo_root)
    fsck(args, onyo_root, quiet=True)

    paths_to_rm = sanitize_paths(args.path, onyo_root)

    if not args.quiet:
        print("The following assets and directories will be deleted:")
        print("\n".join(paths_to_rm))

        if not args.yes:
            response = input("Delete assets? (y/N) ")
            if response not in ['y', 'Y', 'yes']:
                logger.info("Nothing was deleted.")
                sys.exit(0)

    # rm and commit
    repo.git.rm('-r', paths_to_rm)
    # TODO: can this commit message be made more helpful?
    repo.git.commit(m='deleted asset(s)\n\n' + '\n'.join(paths_to_rm))
