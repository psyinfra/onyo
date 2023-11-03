from __future__ import annotations

import copy
import sys
import subprocess

from pathlib import Path
from shlex import quote
from typing import Dict

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


def get_temp_file() -> Path:
    from tempfile import mkstemp
    fd, tmp_path = mkstemp(prefix='onyo_', text=True)
    return Path(tmp_path)


def write_asset_file(path: Path,
                     asset: Dict[str, float | int | str | Path]) -> None:
    content = dict()
    if path.exists():
        # For comment roundtrip mode, first read existing file content
        # to get ruamel.yaml's CommentedMap object and edit this rather
        # than dumping the incoming dict as is, which would kill
        # existing comments.
        content = get_asset_content(path)
        if content:
            keys_to_remove = [k for k in content.keys() if k not in asset.keys()]
            for k in keys_to_remove:
                del content[k]
            content.update(asset)
    if not content:
        # The file may have existed, but empty.
        content = asset
    path.open('w').write(dict_to_yaml(content))


def get_asset_content(asset_file: Path) -> dict[str, float | int | str | Path]:
    yaml = YAML(typ='rt', pure=True)
    contents = dict()
    try:
        contents = yaml.load(asset_file)
    except scanner.ScannerError as e:
        ui.print(e)
    if contents is None:
        return dict()
    return contents


# TODO: Fuse with above
def yaml_to_dict(path: Path) -> dict[str, float | int | str | Path]:
    yaml = YAML(typ='rt', pure=True)
    content = yaml.load(path)  # raises scanner.ScannerError
    if content is None:
        content = dict()
    return content


def dict_to_yaml(d: Dict[str, float | int | str | Path]) -> str:
    # ignore reserved keys and pseudo keys, but keep comments for roundtrip,
    # when `d` is a `ruamel.yaml.comments.CommentedMap`
    # TODO: This implies "dict_to_asset_yaml" instead?! (Or account for pseudo- and reserved keys outside)
    content = copy.deepcopy(d)
    for k in NEW_PSEUDO_KEYS + RESERVED_KEYS:
        if k in content.keys():
            del content[k]

    from io import StringIO
    yaml = YAML(typ='rt')
    s = StringIO()
    yaml.dump(content,
              s)
    return s.getvalue()
