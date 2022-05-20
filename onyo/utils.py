import subprocess
import logging
import os
import sys
import shlex
import glob
import yaml

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
                run_cmd("mv \"" + temp_file + "\" \"" + file + "\"")
                return
            except yaml.YAMLError:
                logger.error(file + " is no legal yaml syntax.")
                while True:
                    further_editing = str(input("Continue editing? (y/n)"))
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
