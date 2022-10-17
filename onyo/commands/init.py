import logging
import sys
import shutil
from pathlib import Path
import git

logging.basicConfig()
log = logging.getLogger('onyo')


def get_skel_dir():
    """
    Return the path of the skel/ dir in the onyo module directory.
    """
    onyo_module_dir = Path(__file__).resolve().parent.parent
    skel = Path(onyo_module_dir, 'skel')
    return skel


def sanitize_dir(directory, onyo_root):
    """
    Check the directory for viability as an init target.

    Returns the absolute path on success.
    """
    full_dir = Path(onyo_root)
    if directory:
        full_dir = Path(onyo_root, directory)

    # sanity checks
    # already an .onyo repo
    dot_onyo = full_dir.joinpath('.onyo')
    if dot_onyo.is_dir():
        log.error(f"'{dot_onyo}' already exists. Exiting.")
        sys.exit(1)

    # target is a file, etc
    if full_dir.exists() and not full_dir.is_dir():
        log.error(f"'{full_dir}' exists but is not a directory. Exiting.")
        sys.exit(1)

    # make sure parent exists
    if not full_dir.is_dir():
        parent_dir = full_dir.parent
        if not parent_dir.is_dir():
            log.error(f"'{parent_dir}' does not exist. Exiting.")
            sys.exit(1)

    abs_dir = str(full_dir.resolve())
    return abs_dir


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
        log.info(target_dir + " has a git repository.")
    except git.exc.InvalidGitRepositoryError:
        repo = git.Repo.init(target_dir)

    # populate .onyo dir
    skel = get_skel_dir()
    dot_onyo = Path(target_dir, ".onyo")
    shutil.copytree(skel, dot_onyo)

    # add and commit
    repo.git.add('.onyo/')
    repo.git.commit(m='initialize onyo repository')

    # print success
    abs_dot_onyo = str(dot_onyo.resolve())
    print(f'Initialized Onyo repository in {abs_dot_onyo}')
