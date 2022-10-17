import logging
import os
import sys
import glob
import yaml

from git import Repo, exc

from onyo.utils import (
    run_cmd,
    get_list_of_assets,
    get_git_root,
    validate_file
)

logging.basicConfig()
log = logging.getLogger('onyo')


def verify_onyo_existence(onyo_root):
    info_str = ""
    try:
        git_repo = Repo(onyo_root, search_parent_directories=True)
        repo_path = git_repo.git.rev_parse("--show-toplevel")
        repo = Repo(repo_path)
        info_str = info_str + "onyo repo: " + repo_path
    except exc.InvalidGitRepositoryError:
        log.error(onyo_root + " is not a valid git repository.")
        sys.exit(1)
    if not os.path.exists(os.path.join(repo_path, ".onyo")):
        log.error(repo_path + " is not a valid onyo repository.")
        sys.exit(1)
    return [repo, repo_path, info_str]


def verify_onyo_working_tree(repo):
    # set variables
    problem_str = ""
    changed_files = [item.a_path for item in repo.index.diff(None)]
    untracked_files = repo.untracked_files
    staged_files = [item.a_path for item in repo.index.diff("HEAD")]
    # list problems
    if len(changed_files) != 0 or len(untracked_files) != 0 or len(staged_files) != 0:
        problem_str = problem_str + "\nThe Onyo working tree is not clean."
        if len(staged_files) != 0:
            problem_str = problem_str + "\nChanges to be committed: \n\t " + "\n\t ".join(staged_files)
        if len(changed_files) != 0:
            problem_str = problem_str + "\nChanges not staged for commit: \n\t " + "\n\t ".join(changed_files)
        if len(untracked_files) != 0:
            problem_str = problem_str + "\nUntracked files: \n\t " + "\n\t ".join(untracked_files)
        problem_str = problem_str + "\nPlease commit all changes or add new files to .gitignore"
    return problem_str


def verify_anchors(onyo_root):
    anchor_str = ""
    for elem in glob.iglob(onyo_root + '**/**', recursive=True):
        if os.path.isdir(elem):
            # the .git does not need a .anchor
            if ".git" in elem:
                continue
            # the onyo root folder has no .anchor
            if os.path.samefile(elem, onyo_root):
                continue
            if run_cmd("git -C \"" + onyo_root + "\" check-ignore --no-index \"" + elem + "\""):
                continue
            if not os.path.isfile(os.path.join(elem, ".anchor")):
                anchor_str = anchor_str + "\n\t" + os.path.relpath(os.path.join(elem, ".anchor"), onyo_root)
    if anchor_str:
        return "\n\n.anchor is missing:" + anchor_str + "\nYou can create them with\ntouch <path/to/.anchor>\nor .gitignore the directories.\n"
    return ""


def verify_yaml(onyo_root):
    yaml_str = ""
    for elem in glob.iglob(onyo_root + '**/**', recursive=True):
        if os.path.isfile(elem):
            if run_cmd("git -C \"" + onyo_root + "\" check-ignore --no-index \"" + elem + "\""):
                continue
            # "assets" saves all names/paths, to later check if they are unique
            with open(elem, "r") as stream:
                try:
                    yaml.safe_load(stream)
                except yaml.YAMLError:
                    yaml_str = yaml_str + "\t" + os.path.relpath(elem, onyo_root) + "\n"
    if yaml_str:
        return "\n\nyaml files with incorrect syntax:\n" + yaml_str + "Please correct the syntax of these files and add the changes to git, or .gitignore them."
    return ""


def verify_filenames(onyo_root):
    problem_str = ""
    assets = get_list_of_assets(onyo_root)
    double_elements = []
    for elem in [i[1] for i in assets]:
        elements = [string for string in [i[0] for i in assets] if elem == os.path.basename(string)]
        if len(elements) != 1:
            double_elements.append(elements)
    if double_elements:
        double_elements = [list(tupl) for tupl in {tuple(item) for item in double_elements}]
        problem_str = problem_str + "\n\nAsset files must be unique:\n"
        for i in double_elements:
            problem_str = problem_str + "\t" + i[0] + "\n\t\t" + i[1] + "\n"
    if problem_str:
        return problem_str + "Please change file names to unique and valid asset names and add them to git, or .gitignore them.\n"
    else:
        return ""


# validate the asset contents based on .onyo/validation/
def validate_assets(onyo_root):
    problem_str = ""
    assets = get_list_of_assets(onyo_root)
    for asset_file in assets:
        problem_str += validate_file(asset_file[0], os.path.relpath(asset_file[0], onyo_root), onyo_root)
    if problem_str != "":
        return "\nSome files have invalid contents:\n" + problem_str
    return problem_str


def read_only_fsck(args, onyo_root, quiet=False):
    # set variables
    repo = ""
    repo_path = ""
    problem_str = ""
    info_str = ""
    # check if is git, and .git and .onyo exist, identify top-level of onyo directory
    [repo, repo_path, info_str] = verify_onyo_existence(get_git_root(onyo_root))
    # check if it is possible to load yaml file for syntax check
    problem_str = problem_str + verify_yaml(onyo_root)
    # end block, display problems or state repo is clean.
    if problem_str:
        log.error(problem_str)
        sys.exit(1)
    else:
        problem_str = "\nOnyo expects a clean onyo working tree before running commands. Please commit or .gitignore all changes and check the syntax of asset files.\n" + problem_str
        info_str = info_str + "\n" + onyo_root + " is clean."
        if not quiet:
            print(info_str)


def fsck(args, onyo_root, quiet=False):
    """
    Runs a comprehensive suite of checks to verify the integrity and validity of
    an onyo repository and its contents:

    First, ``onyo fsck`` checks if it's a valid git repository and contains an
    ``.onyo`` folder). If either of these fail, Onyo will error immediately and
    exit.

    If the repository valid, the following checks are performed, and all
    problems are listed:

    - all asset names are unique
    - all files are valid YAML
    - all files follow the rules specified in
      ``.onyo/validation/validation.yaml``
    - the git working tree is clean (no untracked or changed files)
    - all directories and sub-directories have a .anchor file

    Files and directories matching rules in ``.gitignore`` will not be checked
    for validity.
    """

    # set variables
    repo = ""
    repo_path = ""
    problem_str = ""
    info_str = ""
    # check if is git, and .git and .onyo exist, identify top-level of onyo directory
    [repo, repo_path, info_str] = verify_onyo_existence(get_git_root(onyo_root))
    # check if git status is clean
    problem_str = problem_str + verify_onyo_working_tree(repo)
    # onyo anchor check for all folders
    problem_str = problem_str + verify_anchors(repo_path)
    # check if it is possible to load yaml file for syntax check
    problem_str = problem_str + verify_yaml(repo_path)
    # check uniqueness of asset filenames
    problem_str = problem_str + verify_filenames(repo_path)
    # validate contents of all files with the validation-file
    problem_str = problem_str + validate_assets(repo_path)

    # end block, display problems or state repo is clean.
    if problem_str:
        problem_str = "\nOnyo expects a clean onyo working tree before running commands. Please commit or .gitignore all changes and check the syntax of asset files.\n" + problem_str
        log.error(problem_str)
        sys.exit(1)
    else:
        info_str = info_str + "\n" + repo_path + " is clean."
        if not quiet:
            print(info_str)
