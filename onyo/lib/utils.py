from __future__ import annotations

import sys
import subprocess

from pathlib import Path
from shlex import quote
from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo.lib.ui import ui
from onyo.lib.consts import NEW_PSEUDO_KEYS, RESERVED_KEYS


def anything2bool(val):
    """Convert various representations of boolean values into actual bool."""
    # Credit: datalad

    if hasattr(val, 'lower'):
        val = val.lower()
    if val in {"off", "no", "false", "0"} or not bool(val):
        return False
    elif val in {"on", "yes", "true", True} \
            or (hasattr(val, 'isdigit') and val.isdigit() and int(val)) \
            or isinstance(val, int) and val:
        return True
    else:
        raise TypeError(
            "Got value %s which could not be interpreted as a boolean"
            % repr(val))


def edit_asset(asset: dict,
               editor: str) -> dict:
    """Edit `asset` with a file editor.

    This is using a temporary YAML file, prefilled with the current content
    of `asset`. Validation of the asset is included.

    Parameters
    ----------

    Returns
    -------

    Raises
    ------
    """
    # TODO: WE DO NOT END UP HERE, WHEN THERE WAS NO ASSET CONTENT DEFINED YET!
    # TODO: name generation/validation into edit routine! (Incl. available paths!)
    # get a tempfile
    from tempfile import mkstemp
    from .assets import write_asset_file, get_asset_content
    fd, tmp_path = mkstemp(prefix='onyo_', text=True)
    tmp_path = Path(tmp_path)
    # We must not write pseudo-keys to the file:
    asset_content = {k: v for k, v in asset.items() if k not in NEW_PSEUDO_KEYS + RESERVED_KEYS}
    write_asset_file(tmp_path, dict(**asset_content))

    edit_asset_file(editor, tmp_path)  # TODO: This returns False on "discard changes". Figure this out.
    #       Also: May be useful to return content dict. Because `edit_asset` is
    #       reading the content afterwards already for validation.
    #       Hence, currently read twice (see below).
    # reload from tempfile
    asset = get_asset_content(tmp_path)
    return asset


def edit_asset_file(editor: str,
                    path: Path) -> bool:
    """Open an existing file at `path` with `editor`. After changes are made, check the
    file content for validity as an asset file. If valid, write the changes,
    otherwise open a dialog and ask the user if the asset should be corrected
    or the changes discarded.

    Returns True when the file was changed and saved without errors, and False
    if the user wants to discard the changes.
    """
    # TODO: Fuse with edit_asset_file above (RF'd for `onyo new`, to be adjusted for `onyo edit`)

    while True:
        # Note: shell=True would be needed for a setting like the one used in tests:
        #       EDITOR="printf 'some: thing' >>". Piping needs either shell, or we must
        #       understand what needs piping at the python level here and create several
        #       subprocesses piped together.
        subprocess.run(f'{editor} {quote(str(path))}', check=True, shell=True)
        try:
            YAML(typ='rt').load(path)
            # TODO: add asset validation here
            return True
        except scanner.ScannerError:
            ui.print(f"{path} has invalid YAML syntax.", file=sys.stderr)
            if not ui.request_user_response("Continue editing? No discards changes. (y/n) "):
                return False


def deduplicate(sequence: list) -> list:
    """Get a deduplicated list, while preserving order."""
    seen = set()
    return [x for x in sequence if not (x in seen or seen.add(x))]
