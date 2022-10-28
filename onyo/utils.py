import logging
import os
import random
import string
from pathlib import Path
from git import Repo, exc

logging.basicConfig()
log = logging.getLogger('onyo')


def generate_faux_serial(repo_root, faux_length=8):
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
    list_of_assets = get_list_of_assets(repo_root)
    faux = "faux" + ''.join(random.choices(alphanum, k=faux_length))
    while True in [faux in asset[1] for asset in list_of_assets]:
        faux = "faux" + ''.join(random.choices(alphanum, k=faux_length))
    return faux


def get_config_value(name, repo_root):
    """
    Get the value for a configuration option specified by `name`. git-config is
    checked first, as it is machine-local. The default order of git-config
    checks is retained. If that is empty, then the .onyo/config file is checked.

    Returns a string with the config value on success. None otherwise.
    """
    value = None
    repo = Repo(repo_root)

    # git-config (with its full stack of locations to check)
    try:
        value = repo.git.config('--get', name)
        log.debug(f"git config acquired '{name}': '{value}'")
    except exc.GitCommandError:
        log.debug(f"git config missed '{name}'")
        pass

    # .onyo/config
    if not value:
        dot_onyo_config = os.path.join(repo_root, '.onyo/config')
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


def get_list_of_assets(repo_root):
    """
    Return a list of all assets in an onyo repository.
    """
    return [[x[0][0], Path(x[0][0]).name] for x in Repo(repo_root).index.entries.items()
            if not is_protected_path(x[0][0])]
