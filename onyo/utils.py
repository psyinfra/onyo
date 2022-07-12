import subprocess
import logging
import os
import sys
import shlex
import glob
import yaml
from ruamel.yaml import YAML

from git import Repo, exc

logging.basicConfig()
logger = logging.getLogger('onyo')


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
        logger.error(run_error)
        sys.exit(1)
    else:
        logger.debug(cmd + " " + comment)
    return run_output


# checks if a given path is git-directory (needs to be main-level)
def is_git_dir(directory):
    try:
        Repo(directory).git_dir
        return True
    except exc.InvalidGitRepositoryError:
        return False


def get_git_root(path):
    # first checks if file is in git from current position
    try:
        git_repo = Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        if os.path.isdir(os.path.join(git_root, ".onyo")):
            return git_root
        else:
            raise exc.InvalidGitRepositoryError
    # otherwise checks if given file relative to $ONYO_REPOSITORY_DIR is in a
    # git repository
    except (exc.NoSuchPathError, exc.InvalidGitRepositoryError):
        onyo_path = os.environ.get('ONYO_REPOSITORY_DIR')
        if onyo_path is None:
            logger.error(path + " is no onyo repository.")
            sys.exit(1)
        elif not is_git_dir(onyo_path):
            logger.error(path + " is no onyo repository.")
            sys.exit(1)

        git_repo = Repo(os.path.join(path, onyo_path),
                        search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        return git_root


def get_full_filepath(git_directory, file):
    full_filepath = os.path.join(git_directory, file)
    if not os.path.exists(full_filepath):
        full_filepath = os.path.join(git_directory, os.getcwd())
        full_filepath = os.path.join(full_filepath, file)
    if not os.path.exists(full_filepath):
        logger.error(file + " not found.")
        sys.exit(1)
    return full_filepath


def get_editor():
    editor = os.environ.get('EDITOR')
    if not editor:
        logger.info("$EDITOR is not set.")
    elif editor and run_cmd("which " + editor).rstrip("\n") == "":
        logger.warning(editor + " could not be found.")
    else:
        return editor
    # try using vi/nano as editor
    if run_cmd("which nano").rstrip("\n") != "":
        logger.info("nano is used as editor.")
        editor = 'nano'
    elif run_cmd("which vi").rstrip("\n") != "":
        logger.info("vi is used as editor.")
        editor = 'vi'
    # if no editor is set, and nano/vi both are not found.
    else:
        logger.error("No editor found.")
        sys.exit(1)
    return editor


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
                            current_error = current_error + "\t" + original_file + " (" + path_of_rule + "): values for \"" + value_field + "\" must be str, but is \"" + str(asset[value_field]) + "\"\n"
                    elif field2 == "int":
                        if not check_int(asset[value_field]):
                            current_error = current_error + "\t" + original_file + " (" + path_of_rule + "): values for \"" + value_field + "\" must be int, but is \"" + str(asset[value_field]) + "\"\n"
                    elif field2 == "float":
                        if not check_float(asset[value_field]):
                            current_error = current_error + "\t" + original_file + " (" + path_of_rule + "): values for \"" + value_field + "\" must be float, but is \"" + str(asset[value_field]) + "\"\n"
                    else:
                        current_error = current_error + "\t" + original_file + " (" + path_of_rule + "): Type \"" + field2 + "\" is not known.\n"

    # return all errors
    return current_error


def validate_file(file, original_file, onyo_root):
    yaml = YAML(typ='safe')
    error_str = ""
    with open(os.path.join(onyo_root, ".onyo/validation/validation.yaml"), "r") as stream:
        try:
            rules_file = yaml.load(stream)
        except yaml.YAMLError as e:
            print(e)
    for path_of_rule in rules_file:
        paths = glob.glob(os.path.join(onyo_root, path_of_rule), recursive=True)
        for elem in paths:
            if error_str != "":
                return error_str
            # when a rule applies to original_file:
            if original_file in elem:
                for rule in rules_file[path_of_rule]:
                    error_str = error_str + validate_rule_for_file(file, rule, path_of_rule, original_file, onyo_root)
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


def edit_file(file, onyo_root):
    if not os.path.isfile(file):
        logger.error(file + " does not exist.")
        sys.exit(1)
    # create and edit a temporary file, and if that is valid replace original
    temp_file = os.path.join(onyo_root, os.path.join(".onyo/temp/", os.path.basename(file)))
    if not os.path.isfile(temp_file):
        run_cmd("cp \"" + file + "\" \"" + temp_file + "\"")
    # When temp-file exists, ask if to use it
    elif os.path.isfile(temp_file):
        while True:
            edit_temp = str(input("Temporary changes for " + file + " exist. Continue editing? (y/n)"))
            if edit_temp == 'y':
                break
            elif edit_temp == 'n':
                run_cmd("cp \"" + file + "\" \"" + temp_file + "\"")
                break
    further_editing = 'y'
    while further_editing == 'y':
        # do actual editing:
        os.system(get_editor() + " \"" + temp_file + "\"")
        # check syntax
        with open(temp_file, "r") as stream:
            try:
                yaml.safe_load(stream)
                problem_str = validate_file(temp_file, file, onyo_root)
                if problem_str == "":
                    run_cmd("mv \"" + temp_file + "\" \"" + file + "\"")
                else:
                    # TODO: better exception needed
                    raise yaml.YAMLError("\nOnyo Validation failed for:\n" + problem_str)
                return
            except yaml.YAMLError as e:
                while True:
                    further_editing = str(input(str(e) + "Continue editing? (y/n)"))
                    if further_editing == 'y':
                        break
                    elif further_editing == 'n':
                        run_cmd("rm \"" + temp_file + "\"")
                        logger.info("No changes made.")
                        sys.exit(1)
    return


def build_git_add_cmd(directory, file):
    return "git -C \"" + directory + "\" add \"" + file + "\""


def get_list_of_assets(repo_path):
    assets = []
    for elem in glob.iglob(repo_path + '**/**', recursive=True):
        if os.path.isfile(elem):
            # when assets are in .gitignore, they should not be listed as such
            if run_cmd("git -C \"" + repo_path + "\" check-ignore --no-index \"" + elem + "\""):
                continue
            assets.append([os.path.relpath(elem, repo_path), os.path.basename(elem)])
    return assets


def prepare_directory(directory):
    if os.path.isdir(os.path.join(os.getcwd(), directory)):
        location = os.path.join(os.getcwd(), directory)
    elif os.environ.get('ONYO_REPOSITORY_DIR') is not None and os.path.isdir(os.path.join(os.environ.get('ONYO_REPOSITORY_DIR'), directory)) and os.path.isdir(os.path.join(get_git_root(directory), directory)):
        location = os.path.join(get_git_root(directory), directory)
    else:
        logger.error(directory + " does not exist.")
        sys.exit(1)
    return location
