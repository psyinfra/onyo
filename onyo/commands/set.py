import logging
import os
import sys
from ruamel.yaml import YAML  # pyre-ignore[21]

from onyo import Repo, OnyoInvalidRepoError

logging.basicConfig()
log = logging.getLogger('onyo')


def read_asset(file, opdir):
    yaml = YAML(typ='rt')
    asset = {}
    with open(os.path.join(opdir, file), "r") as stream:
        try:
            asset = yaml.load(stream)
        except yaml.YAMLError as e:
            print(e)
    if asset is None:
        return {}
    return asset


def write_asset(data, file, opdir):
    yaml = YAML(typ='rt')
    with open(os.path.join(opdir, file), "w") as stream:
        yaml.dump(data, stream)


def set_value(file, git_filepath, keys, opdir):
    asset = read_asset(git_filepath, opdir)
    for key in keys.items():
        try:
            asset[key[0]] = key[1]
        # when a YAML asset just has a line with a key like "RAM" without value:
        except TypeError as e:
            return "Can't update asset " + git_filepath + ": " + str(e)
    write_asset(asset, git_filepath, opdir)
    return ""


def add_assets_from_directory(directory, asset_list, depth, opdir):
    for path in os.listdir(os.path.join(opdir, directory)):
        asset = os.path.join(os.path.join(opdir, directory), path)
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
                asset_list = add_assets_from_directory(os.path.join(directory, path), asset_list, depth, opdir)
    return asset_list


def diff_changes(file_list, keys, opdir):
    output_str = ""
    asset = []
    yaml = YAML(typ='rt')
    for file in file_list:
        with open(os.path.join(opdir, file), "r") as stream:
            try:
                asset = yaml.load(stream)
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
            if opdir in file:
                output_str = output_str + "\n" + os.path.relpath(file, opdir) + asset_changed
            else:
                output_str = output_str + "\n" + file + asset_changed
    return output_str


def prepare_arguments(path, keys, quiet, yes, recursive, depth, opdir):
    problem_str = ""
    asset_list = []
    if quiet and not yes:
        problem_str = problem_str + "\nonyo set --quiet can't be run without --yes flag."
    if not depth == -1 and not depth > 0:
        problem_str = problem_str + "\n--depth must be an integer bigger than 0."
    for file in path:
        asset = os.path.join(opdir, file)
        # if "onyo set RAM=10 *" is called, directories should not throw an
        # error, but also not be added to the asset list.
        if os.path.isdir(asset):
            if recursive:
                if file == ".":
                    asset_list = add_assets_from_directory(opdir, asset_list, depth, opdir)
                else:
                    asset_list = add_assets_from_directory(file, asset_list, depth, opdir)
            else:
                log.info("Can't set values for folder \"" + file + "\" without --recursive flag.\n")
            continue
        if not os.path.isfile(asset):
            problem_str = problem_str + "\nAsset file " + file + " does not exist."
            continue
        asset_list.append(file)
    # TODO: validate assets
    if len(asset_list) == 0:
        problem_str = problem_str + "\nNo assets selected."
    if problem_str != "":
        log.error(problem_str)
        sys.exit(1)
    asset_list.sort()
    return asset_list


def set(args, opdir):
    """
    Set the ``value`` of ``key`` for matching assets. If the key does not exist,
    it is added and set appropriately.

    Key names can be any valid YAML key name.

    Multiple ``key=value`` pairs can be declared by joining with a ``,``. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used. If Onyo is invoked from outside of the Onyo repository, the root of
    the repository is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """
    try:
        repo = Repo(opdir)
        # don't run onyo fsck, so values can be set for correcting assets.
        # TODO: really?
    except OnyoInvalidRepoError:
        sys.exit(1)

    # get all files in which the values should be set/changed
    files_to_change = prepare_arguments(args.path, args.keys, args.quiet, args.yes, args.recursive, args.depth, opdir)
    if not args.quiet:
        diff_output = diff_changes(files_to_change, args.keys, opdir)
        if diff_output:
            print("onyo wants to update the following assets:")
            print(diff_output)
        # The else happens, if valid assets are selected, but no values are to
        # be updated (e.g. `onyo set RAM=10`, but assets have already RAM: 10)
        else:
            log.warning("The values are already set. No assets updated.")
            sys.exit(0)
    if args.dry_run:
        sys.exit(0)
    if not args.yes:
        update_input = str(input("Update assets? (y/N) "))
        if update_input not in ['y', 'Y', 'yes']:
            log.info("No assets updated.")
            sys.exit(0)

    for file in files_to_change:
        set_value(os.path.join(opdir, file), file, args.keys, opdir)
        # add any changes
        repo.add(file)

    files_staged = [str(x) for x in repo.files_staged]
    if files_staged:
        repo.commit('set values', files_staged)
