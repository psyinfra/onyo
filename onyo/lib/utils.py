from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo.lib.consts import PSEUDO_KEYS, RESERVED_KEYS
from onyo.lib.ui import ui


def deduplicate(sequence: list | None) -> list | None:
    """Get a deduplicated list, while preserving order.

    For ease of use, accepts `None` (and returns it in that case).
    """
    if not sequence:
        return sequence
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
        ui.error(f"{asset_file} has invalid YAML syntax: {str(e)}")
    if contents is None:
        return dict()
    return contents


# TODO: Fuse with get_asset_content. Note different error behavior, though.
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
    for k in PSEUDO_KEYS + RESERVED_KEYS:
        if k in content.keys():
            del content[k]

    from io import StringIO
    yaml = YAML(typ='rt')
    s = StringIO()
    yaml.dump(content,
              s)
    return s.getvalue()
