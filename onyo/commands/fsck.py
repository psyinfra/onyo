import sys

from onyo.lib import Repo, OnyoInvalidRepoError


def fsck(args, onyo_root):
    """
    Run a suite of checks to verify the integrity and validity of an Onyo
    repository and its contents.

    By default, the following tests will be performed:

    - "clean-tree": verifies that the git tree is clean ---that there are
      no changed (staged or unstaged) nor untracked files.
    - "anchors": verifies that all folders (outside of .onyo) have an
      .anchor file
    - "asset-unique": verifies that all asset names are unique
    - "asset-yaml": loads each assets and checks if it's valid YAML
    - "asset-validity": loads each asset and validates the contents against
      the validation rulesets defined in ``.onyo/validation/validation.yaml``.
    """
    try:
        repo = Repo(onyo_root)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)
