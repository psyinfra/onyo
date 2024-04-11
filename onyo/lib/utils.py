from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Dict,
        Set,
    )


def deduplicate(sequence: list | None) -> list | None:
    r"""Deduplicate a list and preserve its order.

    The first occurrence of a value is kept. All later occurrences are
    discarded.

    For convenience, also accepts ``None`` and returns ``None`` in that case.

    Parameters
    ----------
    sequence
        List to deduplicate.
    """
    if not sequence:
        return sequence
    seen = set()
    return [x for x in sequence if not (x in seen or seen.add(x))]


def dict_to_asset_yaml(d: Dict[str, bool | float | int | str | Path]) -> str:
    r"""Convert a dictionary to a YAML string, stripped of reserved-keys.

    Dictionaries that contain a map of comments (ruamel, etc) will have those
    comments included in the string.

    See Also
    --------
    onyo.lib.consts.RESERVED_KEYS

    Parameters
    ----------
    d
        Dictionary to strip of reserved-keys and convert to a YAML string.
    """
    # deepcopy to keep comments when `d` is `ruamel.yaml.comments.CommentedMap`.
    content = copy.deepcopy(d)
    for k in PSEUDO_KEYS + RESERVED_KEYS:
        if k in content.keys():
            del content[k]

    from io import StringIO
    yaml = YAML(typ='rt')
    s = StringIO()
    yaml.dump(content,
              s)
    return s.getvalue()


def get_asset_content(asset_file: Path) -> dict[str, bool | float | int | str | Path]:
    r"""Get the contents of an asset as a dictionary.

    If the asset file's contents are not valid YAML, an error is printed.

    Parameters
    ----------
    asset_file
        The Path of the asset file to get the contents of.
    """
    yaml = YAML(typ='rt', pure=True)
    contents = dict()
    try:
        contents = yaml.load(asset_file)
    except scanner.ScannerError as e:
        ui.error(f"{asset_file} has invalid YAML syntax: {str(e)}")
    if contents is None:
        return dict()
    return contents


def get_temp_file() -> Path:
    r"""Create and return the Path of a new temporary file.
    """
    from tempfile import mkstemp
    fd, tmp_path = mkstemp(prefix='onyo_', text=True)
    return Path(tmp_path)


def has_unique_names(asset_files: Set[Path]) -> bool:
    r"""Check files for unique file names.

    If duplicates are found, an error is printed listing them.

    Parameters
    ----------
    asset_files
        A set of files to check for the uniqueness of their file names.
    """
    asset_names = [a.name for a in asset_files]
    duplicates = [a for a in asset_files if asset_names.count(a.name) > 1]
    duplicates.sort(key=lambda x: x.name)

    if duplicates:
        ui.error('The following file names are not unique:\n{}'.format(
            '\n'.join(map(str, duplicates))))
        return False

    return True


def validate_yaml(asset_files: list[Path] | None) -> bool:
    r"""Check files for valid YAML.

    If files with invalid YAML are detected, an error is printed listing them.

    Parameters
    ----------
    asset_files
        A list of files to check for valid YAML.
    """
    # Note: Does not (and cannot) account for asset dirs automatically in this form.
    #       Thus needs to be done by caller.
    # Note: assumes absolute paths!
    invalid_yaml = []
    asset_files = asset_files or []
    for asset in asset_files:
        # TODO: use valid_yaml()
        try:
            YAML(typ='rt').load(asset)
        except scanner.ScannerError:
            invalid_yaml.append(str(asset))

    if invalid_yaml:
        ui.error('The following files fail YAML validation:\n{}'.format(
            '\n'.join(invalid_yaml)))
        return False

    return True


def write_asset_file(path: Path,
                     asset: Dict[str, bool | float | int | str | Path]) -> None:
    r"""Write content to an asset file.

    All ``RESERVED_KEYS`` will be stripped from the content before writing.

    Parameters
    ----------
    path
        The Path to write content to.
    asset
        A dictionary of content to write to the path.
    """
    path.open('w').write(dict_to_asset_yaml(asset))
