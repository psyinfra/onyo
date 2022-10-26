import subprocess
import logging
import os
import sys
import shlex
import glob
import yaml
import string
import random
from pathlib import Path
from ruamel.yaml import YAML  # pyre-ignore[21]
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


def validate_rule_for_file(file, rule, path_of_rule, original_file, onyo_root):
    asset = ""
    current_error = ""
    yaml = YAML(typ='safe')
    with open(os.path.join(onyo_root, file), "r") as stream:
        try:
            asset = yaml.load(stream)
        except yaml.YAMLError as e:
            print(e)
    for value_field in rule:
        for field in rule[value_field]:
            # value == e.g. RAM
            # field1 == e.g. Type
            # field2 == e.g. str
            field1 = list(field)[0]
            field2 = field[field1]
            if asset and value_field in asset:
                if field1 == "Type":
                    if field2 == "str":
                        if not check_str(asset[value_field]):
                            current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): values for \"" + value_field + "\" must be str, but is \"" + str(asset[value_field]) + "\"\n"
                    elif field2 == "int":
                        if not check_int(asset[value_field]):
                            current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): values for \"" + value_field + "\" must be int, but is \"" + str(asset[value_field]) + "\"\n"
                    elif field2 == "float":
                        if not check_float(asset[value_field]):
                            current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): values for \"" + value_field + "\" must be float, but is \"" + str(asset[value_field]) + "\"\n"
                    else:
                        current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): Type \"" + field2 + "\" is not known.\n"
    # return all errors
    return current_error


def validate_file(file, original_file, onyo_root):
    ru_yaml = YAML(typ='safe')
    error_str = ""
    with open(os.path.join(get_git_root(onyo_root), ".onyo/validation/validation.yaml"), "r") as stream:
        try:
            rules_file = ru_yaml.load(stream)
            if not rules_file:
                rules_file = []
        except yaml.YAMLError as e:
            print(e)
    for path_of_rule in rules_file:
        if error_str != "":
            return error_str
        # when a rule applies to original_file:
        if os.path.join(onyo_root, original_file) in glob.glob(os.path.join(onyo_root, path_of_rule), recursive=True):
            for rule in rules_file[path_of_rule]:
                error_str = error_str + validate_rule_for_file(file, rule, path_of_rule, original_file, onyo_root)
            return error_str
    # give error back for outside handling:
    return error_str


# check for a value from a yaml file, if it is a str or can be formatted to it
def check_str(value):
    try:
        if isinstance(value, str):
            return True
        elif isinstance(str(value), str):
            return True
    except Exception:
        return False


# check for a value from a yaml file, if it is a int or can be formatted to it
def check_int(value):
    try:
        if isinstance(value, int):
            return True
        # this happens in other functions, but should be blocked in check_int,
        # since otherwise all floats will be successfully cast to integer.
        # elif isinstance(int(value), int):
        #    return True
    except Exception:
        return False


# check for a value from a yaml file, if it is a float or can be formatted to it
def check_float(value):
    try:
        if isinstance(value, float):
            return True
        elif isinstance(float(value), float):
            return True
    except Exception:
        return False


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
