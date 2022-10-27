import subprocess
import logging
import os
import sys
import shlex
import string
import random
from pathlib import Path
from git import Repo, exc

logging.basicConfig()
log = logging.getLogger('onyo')


def run_cmd(cmd, comment=""):
    if comment != "":
        run_process = subprocess.Popen(shlex.split(cmd) + [comment],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    else:
        run_process = subprocess.Popen(shlex.split(cmd),
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    run_output, run_error = run_process.communicate()
    if (run_error != ""):
        log.error(run_error)
        sys.exit(1)
    else:
        log.debug(cmd + " " + comment)
    return run_output


def get_git_root(path):
    # first checks if file is in git from current position
    try:
        git_repo = Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        if os.path.isdir(os.path.join(git_root, ".onyo")):
            return git_root
    except (exc.NoSuchPathError, exc.InvalidGitRepositoryError):
        log.error(path + " is no onyo repository.")
        sys.exit(1)
        return git_root


def generate_faux_serial(onyo_root, faux_length=8):
    """
    Generate a unique faux serial number and verify that it does not appear in
    any other asset file name in any directory of the onyo repository.
    The requested length of faux serial numbers is limited to the interval
    between 1 and 37.

    Returns on success a unique faux serial number which does not appear in any
    other asset file name in any directory of the repository.
    """
    # check that the requested faux serial number has a valid length
    if faux_length < 1 or faux_length > 37:
        raise ValueError("Length of faux serial numbers must be between 1 and 37")

    # generate a new faux serial number until a unique one (which is in no other
    # asset name in the repository) is found, then return it.
    alphanum = string.ascii_letters + string.digits
    list_of_assets = get_list_of_assets(onyo_root)
    faux = "faux" + ''.join(random.choices(alphanum, k=faux_length))
    while True in [faux in asset[1] for asset in list_of_assets]:
        faux = "faux" + ''.join(random.choices(alphanum, k=faux_length))
    return faux


def build_git_add_cmd(directory, file):
    return "git -C \"" + directory + "\" add \"" + file + "\""


def get_config_value(name, onyo_root):
    """
    Get the value for a configuration option specified by `name`. git-config is
    checked first, as it is machine-local. The default order of git-config
    checks is retained. If that is empty, then the .onyo/config file is checked.

    Returns a string with the config value on success. None otherwise.
    """
    value = None
    repo = Repo(onyo_root)

    # git-config (with its full stack of locations to check)
    try:
        value = repo.git.config('--get', name)
        log.debug(f"git config acquired '{name}': '{value}'")
    except exc.GitCommandError:
        log.debug(f"git config missed '{name}'")
        pass

    # .onyo/config
    if not value:
        dot_onyo_config = os.path.join(repo.git.rev_parse('--show-toplevel'), '.onyo/config')
        try:
            value = repo.git.config('--get', name, f=dot_onyo_config)
            log.debug(f"onyo config acquired '{name}': '{value}'")
        except exc.GitCommandError:
            log.debug(f"onyo config missed '{name}'")
            pass

    # reset to None if empty
    if not value:
        value = None

    return value


def get_list_of_assets(repo_path):
    """
    Return a list of all assets in an onyo repository.
    """
    return [[x[0][0], Path(x[0][0]).name] for x in Repo(repo_path).index.entries.items()
            if not is_protected_path(x[0][0])]


def is_protected_path(path):
    """
    Checks whether a path contains protected elements (.anchor, .git, .onyo).
    Returns True if it contains protected elements. Otherwise False.
    """
    full_path = Path(path).resolve()

    # protected paths
    for p in full_path.parts:
        if p in ['.anchor', '.git', '.onyo']:
            return True

    return False
