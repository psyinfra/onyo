#!/usr/bin/env python3

import logging
import os
import sys
import yaml
import glob
from ruamel.yaml import YAML

from git import Repo

from onyo.utils import (
    run_cmd,
    build_git_add_cmd,
    get_git_root,
    validate_rule_for_file
)

logging.basicConfig()
logger = logging.getLogger('onyo')


def build_commit_cmd(files_to_change, onyo_root):
    return ["git -C \"" + onyo_root + "\" commit -m", "set values.\n\n" +
            "\n".join(files_to_change)]


def read_asset(file, onyo_root):
    yaml = YAML(typ='safe')
    asset = {}
    with open(os.path.join(onyo_root, file), "r") as stream:
        try:
            asset = yaml.load(stream)
        except yaml.YAMLError as e:
            print(e)
    if asset is None:
        return {}
    return asset


def write_asset(data, file, onyo_root):
    with open(os.path.join(onyo_root, file), "w") as stream:
        yaml.dump(data, stream)


def set_value(file, git_filepath, keys, onyo_root):
    asset = read_asset(git_filepath, onyo_root)
    for key in keys.items():
        try:
            asset[key[0]] = key[1]
        # when a YAML asset just has a line with a key like "RAM" without value:
        except TypeError as e:
            return "Can't update asset " + git_filepath + ": " + str(e)
    write_asset(asset, git_filepath, onyo_root)
    return ""


def add_assets_from_directory(directory, asset_list, depth, onyo_root):
    for path in os.listdir(os.path.join(onyo_root, directory)):
        asset = os.path.join(os.path.join(onyo_root, directory), path)
        if path in [".git", ".onyo", ".anchor"]:
            continue
        if os.path.isfile(asset):
            asset_list.append(asset)
        elif os.path.isdir(asset):
            if depth == 0:
                return asset_list
            else:
                if depth > 0:
                    depth = depth - 1
                asset_list = add_assets_from_directory(os.path.join(directory, path), asset_list, depth, onyo_root)
    return asset_list


def diff_changes(file_list, keys, onyo_root):
    output_str = ""
    asset = []
    ru_yaml = YAML(typ='safe')
    for file in file_list:
        with open(os.path.join(onyo_root, file), "r") as stream:
            try:
                asset = ru_yaml.load(stream)
                if not asset:
                    asset = []
            except yaml.YAMLError as e:
                print(e)
        asset_changed = ""
        for key in keys:
            # if the value exists and is the same as before, do nothing:
            if key in asset and asset[key] == keys[key]:
                continue
            # if existing value gets updated, show the removal of the old value:
            if key in asset:
                asset_changed = asset_changed + "\n-\t" + key + ": " + str(asset[key])
            # display new value:
            asset_changed = asset_changed + "\n+\t" + key + ": " + str(keys[key])
        if asset_changed:
            if onyo_root in file:
                output_str = output_str + "\n" + os.path.relpath(file, get_git_root(onyo_root)) + asset_changed
            else:
                output_str = output_str + "\n" + file + asset_changed
    return output_str


def simulate_validation_after_change(file, rules_file, keys, onyo_root):
    problem_str = ""
    temp_file = os.path.join(get_git_root(onyo_root), os.path.join(".onyo/temp/", os.path.basename(file)))
    # either it exists relative from cwd, or else should use the absolute path
    if os.path.isdir(file):
        run_cmd("cp \"" + file + "\" \"" + temp_file + "\"")
    else:
        run_cmd("cp \"" + os.path.join(onyo_root, file) + "\" \"" + temp_file + "\"")
    problem_str = problem_str + set_value(temp_file, temp_file, keys, onyo_root)
    for path_of_rule in rules_file:
        if os.path.join(onyo_root, file) in glob.glob(os.path.join(onyo_root, path_of_rule), recursive=True):
            for rule in rules_file[path_of_rule]:
                problem_str = problem_str + validate_rule_for_file(temp_file, rule, path_of_rule, file, onyo_root)
                if problem_str != "":
                    run_cmd("rm \"" + temp_file + "\"")
                    return problem_str
    run_cmd("rm \"" + temp_file + "\"")
    return problem_str


def prepare_arguments(source, keys, quiet, yes, recursive, depth, onyo_root):
    problem_str = ""
    asset_list = []
    ru_yaml = YAML(typ='safe')
    if quiet and not yes:
        problem_str = problem_str + "\nonyo set --quiet can't be run without --yes flag."
    if not depth == -1 and not depth > 0:
        problem_str = problem_str + "\n--depth must be an integer bigger than 0."
    # just open/validate the rules-file once
    with open(os.path.join(get_git_root(onyo_root), ".onyo/validation/validation.yaml"), "r") as stream:
        try:
            rules_file = ru_yaml.load(stream)
            if not rules_file:
                rules_file = []
        except yaml.YAMLError as e:
            print(e)
    for file in source:
        asset = os.path.join(onyo_root, file)
        # if "onyo set RAM=10 *" is called, directories should not throw an
        # error, but also not be added to the asset list.
        if os.path.isdir(asset):
            if recursive:
                if file == ".":
                    asset_list = add_assets_from_directory(onyo_root, asset_list, depth, onyo_root)
                else:
                    asset_list = add_assets_from_directory(file, asset_list, depth, onyo_root)
            else:
                logger.info("Can't set values for folder \"" + file + "\" without --recursive flag.\n")
            continue
        if not os.path.isfile(asset):
            problem_str = problem_str + "\nAsset File " + file + " does not exist."
            continue
        asset_list.append(file)
    # try validating:
    validation_error_str = ""
    for asset in asset_list:
        validation_error_str = validation_error_str + simulate_validation_after_change(asset, rules_file, keys, onyo_root)
    if validation_error_str != "":
        problem_str = problem_str + "\n" + validation_error_str
    if len(asset_list) == 0:
        problem_str = problem_str + "\nNo assets selected."
    if problem_str != "":
        logger.error(problem_str)
        sys.exit(1)
    return asset_list


def set(args, onyo_root):
    # don't run onyo fsck, so values can be set for correcting assets.
    # fsck(args, onyo_root, quiet=True)
    # get all files in which the values should be set/changed
    files_to_change = prepare_arguments(args.source, args.keys, args.quiet, args.yes, args.recursive, args.depth, onyo_root)
    if not args.quiet:
        diff_output = diff_changes(files_to_change, args.keys, onyo_root)
        if diff_output:
            print("onyo wants to update the following assets:")
            print(diff_output)
        # The else happens, if valid assets are selected, but no values are to
        # be updated (e.g. `onyo set RAM=10`, but assets have already RAM: 10)
        else:
            logger.warning("The values are already set. No Assets updated.")
            sys.exit(0)
    if args.dry_run:
        sys.exit(0)
    if not args.yes:
        update_input = str(input("Update assets? (y/n)"))
        if not update_input == "y":
            logger.info("No assets updated.")
            sys.exit(0)

    for file in files_to_change:
        set_value(os.path.join(onyo_root, file), file, args.keys, onyo_root)
        repo = Repo(onyo_root)
        changed_files = [item.a_path for item in repo.index.diff(None)]
        if len(changed_files) != 0:
            git_add_cmd = build_git_add_cmd(onyo_root, file)
            run_cmd(git_add_cmd)
    # build commit command
    [commit_cmd, commit_msg] = build_commit_cmd(files_to_change, onyo_root)
    # run commands
    run_cmd(commit_cmd, commit_msg)
