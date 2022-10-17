import logging
import sys

from git import Repo, exc
from pathlib import Path
from ruamel.yaml import YAML, scanner

from onyo.utils import (
    get_list_of_assets,
    is_protected_path,
    validate_file
)

logging.basicConfig()
log = logging.getLogger('onyo')


def is_onyo_repo(onyo_root, quiet):
    """
    Checks if the repository is a valid Onyo repository. Returns True or False.
    """
    try:
        repo = Repo(onyo_root, search_parent_directories=True)
    except exc.InvalidGitRepositoryError:
        if not quiet:
            log.error(f"'{onyo_root}' is not a git repository.")

        return False

    repo_path = repo.git.rev_parse("--show-toplevel")
    if not Path(repo_path, '.onyo').is_dir():
        if not quiet:
            log.error(f"'{repo_path}' is not an onyo repository.")

        return False

    # TODO: check .onyo/config, etc

    return True


def is_clean_tree(onyo_root, quiet):
    """
    Checks if the working tree for git is clean. Returns True or False.
    """
    repo = Repo(onyo_root)
    changed = [i.a_path for i in repo.index.diff(None)]
    staged = [i.a_path for i in repo.index.diff("HEAD")]
    untracked = repo.untracked_files

    if changed or staged or untracked:
        if not quiet:
            log.error("The working tree is not clean.")

            if changed:
                log.error("Changes not staged for commit:")
                log.error('\n\t' + '\n\t'.join(changed))

            if staged:
                log.error("Changes to be committed:")
                log.error('\n\t' + '\n\t'.join(staged))

            if untracked:
                log.error("Untracked files:")
                log.error('\n\t' + '\n\t'.join(untracked))

            log.error("Please commit all changes or add untracked files to .gitignore")

        return False

    return True


def verify_anchors(onyo_root, quiet):
    """
    Checks if all dirs (except those in .onyo) contain an .anchor file.
    Returns True or False.
    """
    # anchors in repo
    anchors_exist = {x[0][0] for x in Repo(onyo_root).index.entries.items()
                     if Path(x[0][0]).name == '.anchor' and
                     '.onyo' not in Path(x[0][0]).parts}

    # anchors that should exist
    anchors_expected = {'{}/.anchor'.format(x.relative_to(onyo_root)) for x in Path(onyo_root).glob('**/')
                        if not is_protected_path(x) and
                        not x.samefile(onyo_root)}

    # are any missing
    difference = anchors_expected.difference(anchors_exist)

    if difference:
        if not quiet:
            log.error('The following .anchor files are missing:')
            log.error('\n'.join(difference))
            log.error("Likely 'mkdir' was used to create the directory. Use 'onyo mkdir' instead.")
            # TODO: Prompt the user if they want Onyo to fix it.

        return False

    return True


def verify_yaml(onyo_root, quiet):
    """
    Checks if all assets have valid YAML. Returns True or False.
    """
    invalid_yaml = []

    for asset in get_list_of_assets(onyo_root):
        try:
            YAML().load(Path(onyo_root, asset))
        except scanner.ScannerError:
            invalid_yaml.append(asset)

    if invalid_yaml:
        if not quiet:
            log.error('The following files fail YAML validation:')
            log.error('\n'.join(invalid_yaml))

        return False

    return True


def verify_unique_file_names(onyo_root, quiet):
    """
    Checks if all files have unique names. Returns True or False.
    """
    # TODO: this checks all files. This should only check /assets/.
    files = {x[0][0] for x in Repo(onyo_root).index.entries.items()
             if not is_protected_path(x[0][0])}
    filenames = {}
    for f in files:
        try:
            filenames[Path(f).name].append(f)
        except KeyError:
            filenames[Path(f).name] = [f]

    if len(files) != len(filenames):
        if not quiet:
            log.error('The following file names are not unique:')
            log.error('\n'.join([x for x in filenames
                                 if len(filenames[x] > 1)]))

        return False

    return True


def validate_assets(onyo_root, quiet):
    """
    Checks if all assets pass validation. Returns True or False.
    """
    invalid = {}
    for asset in get_list_of_assets(onyo_root):
        msg = validate_file(asset, asset, onyo_root)
        if msg:
            invalid[asset] = msg

    if invalid:
        if not quiet:
            log.error('The contents of the following files fail validation:')
            log.error('\n'.join([f'{x}\n{invalid[x]}' for x in invalid]))

        return False

    return True


def read_only_fsck(args, onyo_root, quiet=True):
    tests = {
        "asset-yaml": verify_yaml,
    }
    # basic sanity
    if not is_onyo_repo(onyo_root, quiet):
        sys.exit(1)

    # RUN 'EM ALL DOWN!
    for key in tests:
        if not tests[key](onyo_root, quiet):
            sys.exit(1)


def fsck(args, onyo_root, quiet=False):
    """
    Run a suite of checks to verify the integrity and validity of an Onyo
    repository and its contents.

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
    tests = {
        "clean-tree": is_clean_tree,
        "anchors": verify_anchors,
        "asset-unique": verify_unique_file_names,
        "asset-yaml": verify_yaml,
        "asset-validity": validate_assets,
    }

    # basic sanity
    # TODO
    if not is_onyo_repo(onyo_root, quiet):
        sys.exit(1)

    # RUN 'EM ALL DOWN!
    for key in tests:
        print(f'checking {key}')

        if not tests[key](onyo_root, False):
            sys.exit(1)

    # define a list of checks vs functions/methods
    #   ? git fsck?
    # test order?
    # --quiet?
    # --add/remove tests? (--suite all, none, "readonly" (poor name)
    # document in RTD
