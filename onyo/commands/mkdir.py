import sys

from onyo.lib import Repo, OnyoInvalidRepoError, OnyoProtectedPathError


def mkdir(args, onyo_root):
    """
    Create ``directory``\(s). Intermediate directories will be created as needed
    (i.e. parent and child directories can be created in one call).

    An empty ``.anchor`` file is added to each directory, to ensure that git
    tracks it even when empty.

    If the directory already exists, or the path is protected, Onyo will throw
    an error. All checks are performed before creating directories.
    """
    try:
        repo = Repo(onyo_root)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    try:
        repo.mkdir(args.directory)
    except (FileExistsError, OnyoProtectedPathError):
        sys.exit(1)
