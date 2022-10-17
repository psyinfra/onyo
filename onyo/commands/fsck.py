import sys


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
