import logging
import os
import sys
from pathlib import Path
from shlex import quote

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]
from onyo import Repo, OnyoInvalidRepoError

logging.basicConfig()
log = logging.getLogger('onyo')


def get_editor(repo: Repo) -> str:
    """
    Returns the editor, progressing through git, onyo, $EDITOR, and finally
    fallback to "nano".
    """
    # onyo config and git config
    editor = repo.get_config('onyo.core.editor')

    # $EDITOR environment variable
    if not editor:
        log.debug("onyo.core.editor is not set.")
        editor = os.environ.get('EDITOR')

    # fallback to nano
    if not editor:
        log.debug("$EDITOR is also not set.")
        editor = 'nano'

    return editor


def edit_asset(editor: str, asset: Path) -> bool:
    """
    Open an existing asset with `editor`. After changes are made, check the
    asset for validity and check its YAML syntax. If valid, write the changes,
    otherwise open a dialog and ask the user if the asset should be corrected
    or the changes discarded.

    Returns True when the asset was changed and saved without errors, and False
    if the user wants to discard the changes.
    """
    while True:
        os.system(f'{editor} {quote(str(asset))}')
        try:
            YAML(typ='rt').load(asset)
            # TODO: add asset validity here
            return True
        except scanner.ScannerError:
            print(f"{asset} has invalid YAML syntax.", file=sys.stderr)

        if not request_user_response("Continue editing? No discards changes. (y/n) "):
            break

    return False


def request_user_response(question: str) -> bool:
    """
    Opens a dialog for the user and reads an answer from the keyboard.
    Returns True when user answers yes, False when no, and asks again if the
    input is neither.
    """
    while True:
        answer = input(question)
        if answer in ['y', 'Y', 'yes']:
            return True
        elif answer in ['n', 'N', 'no']:
            return False

    return False


def sanitize_assets(assets: list[str], repo: Repo) -> list[Path]:
    """
    Checks for a list of assets if they are valid paths to files that exist as
    onyo assets in the repository.

    Returns a list of Path() objects if the assets exist in the onyo repository.
    """
    valid_assets = []

    for asset in assets:
        asset = Path(asset).resolve().relative_to(repo.root)
        if asset not in repo.assets:
            print(f"\n{asset} is not an asset.", file=sys.stderr)
        else:
            valid_assets.append(asset)

    if len(valid_assets) != len(assets):
        print("\n\nNo asset updated.", file=sys.stderr)
        sys.exit(1)
    return valid_assets


def edit(args, opdir: str) -> None:
    """
    Open the ``asset`` file(s) using the editor specified by "onyo.core.editor",
    the environment variable ``EDITOR``, or ``nano`` (as a final fallback).

    When multiple asset files are given, Onyo will open them in sequence.

    After editing an ``asset``, the contents will be checked for valid YAML and
    also against any matching rules in ``.onyo/validation/``. If problems are
    found, the choice will be offered to reopen the editor to fix them, or abort
    and return to the original state.
    """
    repo = None
    try:
        repo = Repo(opdir)
        # "onyo fsck" is intentionally not run here.
        # This is so "onyo edit" can be used to fix an existing problem. This has
        # benefits over just simply using `vim`, etc directly, as "onyo edit" will
        # validate the contents of the file before saving and committing.
    except OnyoInvalidRepoError:
        sys.exit(1)

    # check and set paths
    assets = sanitize_assets(args.asset, repo)
    editor = get_editor(repo)

    for asset in assets:
        if edit_asset(editor, asset):
            repo.add(asset)
        else:
            """
            If user wants to discard changes, restore the asset's state
            """
            repo._git(['restore', str(asset)])
            print(f"'{asset}' not updated.")

    # commit changes
    staged = sorted(repo.files_staged)
    if staged:
        print(repo._diff_changes())
        if request_user_response("Save changes? No discards all changes. (y/n) "):
            repo.commit('edit asset(s).', staged)
            repo.commit(repo.generate_commit_message(message=args.message, cmd="edit"))
        else:
            repo.restore()
            print('No assets updated.')
