#!/usr/bin/env python3

import logging
import os
import sys
import glob
import yaml

from git import Repo, exc

from onyo.utils import (
    run_cmd,
    get_list_of_assets
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def verify_onyo_existence(onyo_root):
    info_str = ""
    try:
        git_repo = Repo(onyo_root, search_parent_directories=True)
        repo_path = git_repo.git.rev_parse("--show-toplevel")
        repo = Repo(repo_path)
        info_str = info_str + "onyo repo: " + repo_path
    except exc.InvalidGitRepositoryError:
        logger.error(onyo_root + " is not a valid git repository.")
        sys.exit(1)
    if not os.path.exists(os.path.join(repo_path, ".onyo")):
        logger.error(repo_path + " is not a valid onyo repository.")
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


def verify_anchors(repo_path):
    anchor_str = ""
    for elem in glob.iglob(repo_path + '**/**', recursive=True):
        if os.path.isdir(elem):
            # the .git does not need a .anchor
            if ".git" in elem:
                continue
            # the onyo root folder has no .anchor
            if os.path.samefile(elem, repo_path):
                continue
            if run_cmd("git -C " + repo_path + " check-ignore --no-index \"" + elem + "\""):
                continue
            if not os.path.isfile(os.path.join(elem, ".anchor")):
                anchor_str = anchor_str + "\n\t" + os.path.relpath(os.path.join(elem, ".anchor"), repo_path)
    if anchor_str:
        return "\n\n.anchor is missing:" + anchor_str + "\nYou can create them with\ntouch <path/to/.anchor>\nor .gitignore the directories.\n"
    return ""


def verify_yaml(repo_path):
    yaml_str = ""
    for elem in glob.iglob(repo_path + '**/**', recursive=True):
        if os.path.isfile(elem):
            if run_cmd("git -C " + repo_path + " check-ignore --no-index \"" + elem + "\""):
                continue
            # "assets" saves all names/paths, to later check if they are unique
            with open(elem, "r") as stream:
                try:
                    yaml.safe_load(stream)
                except yaml.YAMLError:
                    yaml_str = yaml_str + "\t" + os.path.relpath(elem, repo_path) + "\n"
    if yaml_str:
        return "\n\nyaml files with incorrect syntax:\n" + yaml_str + "Please correct the syntax of these files and add the changes to git, or .gitignore them."
    return ""


def verify_filenames(repo_path):
    problem_str = ""
    assets = get_list_of_assets(repo_path)
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


def read_only_fsck(args, onyo_root, quiet=False):
    # set variables
    repo = ""
    repo_path = ""
    problem_str = ""
    info_str = ""
    # check if is git, and .git and .onyo exist, identify top-level of onyo directory
    [repo, repo_path, info_str] = verify_onyo_existence(onyo_root)
    # check if it is possible to load yaml file for syntax check
    problem_str = problem_str + verify_yaml(repo_path)
    # end block, display problems or state repo is clean.
    if problem_str:
        logger.error(problem_str)
        sys.exit(1)
    else:
        problem_str = "\nOnyo expects a clean onyo working tree before running commands. Please commit or .gitignore all changes and check the syntax of asset files.\n" + problem_str
        info_str = info_str + "\n" + repo_path + " is clean."
        if not quiet:
            print(info_str)


def fsck(args, onyo_root, quiet=False):
    # set variables
    repo = ""
    repo_path = ""
    problem_str = ""
    info_str = ""
    # check if is git, and .git and .onyo exist, identify top-level of onyo directory
    [repo, repo_path, info_str] = verify_onyo_existence(onyo_root)
    # check if git status is clean
    problem_str = problem_str + verify_onyo_working_tree(repo)
    # onyo anchor check for all folders
    problem_str = problem_str + verify_anchors(repo_path)
    # check if it is possible to load yaml file for syntax check
    problem_str = problem_str + verify_yaml(repo_path)
    # check uniqueness of asset filenames
    problem_str = problem_str + verify_filenames(repo_path)
    # end block, display problems or state repo is clean.
    if problem_str:
        problem_str = "\nOnyo expects a clean onyo working tree before running commands. Please commit or .gitignore all changes and check the syntax of asset files.\n" + problem_str
        logger.error(problem_str)
        sys.exit(1)
    else:
        info_str = info_str + "\n" + repo_path + " is clean."
        if not quiet:
            print(info_str)
