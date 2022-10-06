#!/usr/bin/env python3

import logging
import re
import sys
from pathlib import Path
from git import Repo
from onyo.commands.fsck import fsck
from onyo.utils import is_protected_path

logging.basicConfig()
logger = logging.getLogger('onyo')


def move_mode(destination, sources, onyo_root):
    """
    `mv` can be used to either move or rename a file/directory. The mode is not
    explicitly declared by the user, and must be inferred from the arguments.

    Returns True if "move" mode and False if not.
    """
    # can only rename one item
    if len(sources) > 1:
        return True

    if Path(onyo_root, destination).resolve().is_dir():
        return True

    return False


def rename_mode(destination, sources, onyo_root):
    """
    Returns True if "rename" mode and False if not.

    The inverse of `move_mode()`. See its docstring for more information.
    """
    return not move_mode(destination, sources, onyo_root)


def sanity_check_destination(destination, sources, onyo_root):
    """
    Perform a sanity check on the destination. This includes protected paths,
    conflicts, and other pathological scenarios.

    Returns True on success and exits with an error message on failure.
    """
    error_path_conflict = []
    dest_path = Path(onyo_root, destination).resolve()

    if rename_mode(destination, sources, onyo_root):
        """
        Rename mode checks
        """
        # target cannot already exist
        if dest_path.exists():
            logger.error(f"The destination '{dest_path}' exists and would conflict.")
            logger.error("\nExiting. Nothing was moved.")
            sys.exit(1)

        # parent must exist
        if not dest_path.parent.exists():
            logger.error(f"The destination '{dest_path.parent}' does not exist.")
            logger.error("\nExiting. Nothing was moved.")
            sys.exit(1)

        # renaming files is not allowed
        source = Path(sources[0])
        if source.is_file() and source.name != dest_path.name:
            logger.error(f"Cannot rename asset '{source.name}' to '{dest_path.name}'.")
            logger.error("Use 'onyo set' to rename assets.")
            logger.error("\nExiting. Nothing was moved.")
            sys.exit(1)
    else:
        """
        Move mode checks
        """
        # dest must exist
        if not dest_path.exists():
            logger.error(f"The destination '{destination}' does not exist.")
            logger.error("\nExiting. Nothing was moved.")
            sys.exit(1)

        # dest must be a directory
        if not dest_path.is_dir():
            logger.error(f"The destination '{destination}' is not a directory.")
            logger.error("\nExiting. Nothing was moved.")
            sys.exit(1)

    """
    Common checks
    """
    # protected paths
    if is_protected_path(dest_path):
        logger.error(f"The destination '{destination}' is protected by onyo.")
        logger.error("\nExiting. Nothing was moved.")
        sys.exit(1)

    # check for conflicts and generic insanity
    for s in sources:
        src_path = Path(s).resolve()
        new_path = Path(dest_path, src_path.name).resolve()

        # cannot move into self
        if src_path in new_path.parents:
            logger.error(f"Cannot move '{s}' into itself.")
            logger.error("\nExiting. Nothing was moved.")
            sys.exit(1)

        # target paths cannot already exist
        if new_path.exists():
            error_path_conflict.append(s)
            continue

    if error_path_conflict:
        logger.error("The following destinations exist and would conflict:")
        logger.error('\n'.join(error_path_conflict))
        logger.error("\nExiting. Nothing was moved.")
        sys.exit(1)

    return True


def sanitize_sources(sources, onyo_root):
    """
    Check and normalize a list of paths. If any do not exist, or are protected
    paths (.anchor, .git, .onyo), then they will be printed and exit with error.

    Returns a list of normed source paths on success.
    """
    paths_to_mv = []
    error_path_absent = []
    error_path_protected = []

    # validate sources
    for s in sources:
        src_path = Path(onyo_root, s).resolve()

        # paths must exist
        if not src_path.exists():
            error_path_absent.append(s)
            continue

        # protected paths
        if is_protected_path(src_path):
            error_path_protected.append(s)
            continue

        # TODO: ideally, this would return a list of normed paths, relative to
        # the root of the onyo repository (not to be confused with onyo_root).
        # This would allow commit messages that are consistent regardless of
        # where onyo is invoked from.
        norm_path = str(src_path.relative_to(onyo_root))
        paths_to_mv.append(norm_path)

    if error_path_absent:
        logger.error("The following paths do not exist:")
        logger.error('\n'.join(error_path_absent))
        logger.error("\nExiting. Nothing was moved.")
        sys.exit(1)

    if error_path_protected:
        logger.error("The following paths are protected by onyo:")
        logger.error('\n'.join(error_path_protected))
        logger.error("\nExiting. Nothing was moved.")
        sys.exit(1)

    return paths_to_mv


def mv(args, onyo_root):
    """
    Move ``source``\(s) (assets or directories) to the ``destination``
    directory, or rename a ``source`` directory to ``destination``.

    Files cannot be renamed using ``onyo mv``. To do so, use ``onyo set``.
    """
    # check flags
    if args.quiet and not args.yes:
        logger.error("The --quiet flag requires --yes.")
        sys.exit(1)

    repo = Repo(onyo_root)
    fsck(args, onyo_root, quiet=True)

    # sanitize and validate arguments
    paths_to_mv = sanitize_sources(args.source, onyo_root)
    sanity_check_destination(args.destination, args.source, onyo_root)

    if not args.quiet:
        # use git's --dry-run to generate the proposed changes
        ret = repo.git.mv('--dry-run', paths_to_mv + [args.destination])
        print("The following will be moved:")
        print('\n'.join("'{}' -> '{}'".format(*r) for r in re.findall('Renaming (.*) to (.*)', ret)))

        if not args.yes:
            response = input("Move assets? (y/N) ")
            if response not in ['y', 'Y', 'yes']:
                logger.info("Nothing was moved.")
                sys.exit(0)

    # mv and commit
    repo.git.mv(paths_to_mv + [args.destination])
    # TODO: can this commit message be made more helpful?
    repo.git.commit(m='moved asset(s)\n\n' + '\n'.join(paths_to_mv))
