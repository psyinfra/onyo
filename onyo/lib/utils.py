from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import CommentedMap, scanner, YAML  # pyre-ignore[21]
from ruamel.yaml.error import YAMLError  # pyre-ignore[21]

from onyo.lib.exceptions import NotAnAssetError
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Dict,
        Generator,
    )
    from onyo.lib.items import Item


def get_patched_yaml() -> YAML:  # pyre-ignore[11]
    r"""Return a ``YAML`` object that interprets all keys and values as strings.

    With the exception of YAML's nulls, which are typed as ``None``.
    """

    import re
    import ruamel.yaml.resolver  # pyre-ignore[21]
    from ruamel.yaml.util import RegExp  # pyre-ignore[21]

    # Remove all default implicit typing, and replace with one that resolves
    # everything to a string.
    ruamel.yaml.resolver.implicit_resolvers = []
    yaml = YAML(typ='rt', pure=True)

    # YAML nulls are `None`
    yaml.resolver.add_implicit_resolver(
            tag="tag:yaml.org,2002:null",
            regexp=RegExp('''^(?: ~|null|Null|NULL| )$''', re.X),
            first=['~', 'n', 'N', '']
    )
    # true/false are booleans (and ignore YAML's on/off yes/no madness)
    yaml.resolver.add_implicit_resolver(
            tag='tag:yaml.org,2002:bool',
            regexp=RegExp(r'''^(?:true|True|TRUE|false|False|FALSE)$''', re.X),
            first=['t', 'T', 'f', 'F']
    )
    # everything else is a string
    yaml.resolver.add_implicit_resolver(
            tag="tag:yaml.org,2002:str",
            regexp=RegExp('^.*$'),
            first=None
    )

    return yaml


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


def dict_to_yaml(d: Dict) -> str:
    r"""Convert a dictionary to a YAML string.

    Dictionaries that contain a map of comments (ruamel, etc) will have those
    comments included in the string.

    Parameters
    ----------
    d
        Dictionary to render as YAML.
    """

    # empty dicts serialize to '{}'. Hardcode correct empty response.
    if not d:
        return '---\n'

    from io import StringIO

    yaml = get_patched_yaml()
    yaml.explicit_start = True
    s = StringIO()

    yaml.dump(d, s)
    return s.getvalue()


def yaml_to_dict(s: str) -> Dict | CommentedMap:  # pyre-ignore[11]
    r"""Convert a YAML string to a dictionary.

    YAML that contains comments will have them retained as a comment map.

    Parameters
    ----------
    s
        YAML string to load as a dictionary.

    Raises
    ------
    NotAnAssetError
        The YAML is invalid.
    """

    yaml = get_patched_yaml()
    contents = dict()
    try:
        contents = yaml.load(s)
    except YAMLError as e:  # pyre-ignore[66]
        # Remove ruamel usage pointer (see github issue 436)
        if hasattr(e, 'note') and isinstance(e.note, str) and "suppress this check" in e.note:
            e.note = ""
        raise YAMLError(f"Invalid YAML:\n{str(e)}") from e

    if contents is None:
        return dict()

    if not isinstance(contents, (dict, CommentedMap)):
        # For example: a simple text file may technically be valid YAML,
        # but we may get a string instead of dict.
        raise YAMLError(f"Invalid YAML:\n{s}")

    return contents


def get_asset_content(asset_file: Path) -> dict:
    r"""Get the contents of a Path as a dictionary.

    Parameters
    ----------
    asset_file
        Path to get the contents of.

    Raises
    ------
    NotAnAssetError
        The YAML is invalid.
    """

    try:
        contents = yaml_to_dict_multi(asset_file).__next__()
    except StopIteration:
        # no document yielded
        contents = dict()
    return contents


def yaml_to_dict_multi(stream: Path | str) -> Generator[dict | CommentedMap, None, None]:
    """Yield dictionaries from a (potential) multi-document YAML."""
    # TODO: Input should actually be stream (`TextIO` or sth) not str
    #       Figure when utilizing properly via `onyo_new` where things can come in from file or stdin.
    # TODO: Utilize this function in `get_asset_content` by retrieving only the first document and ignore the rest.
    yaml = get_patched_yaml()
    try:
        for document in yaml.load_all(stream):
            if not isinstance(document, (dict, CommentedMap)):
                # TODO: Better error. See also get_asset_content
                raise NotAnAssetError("Invalid item in YAML document.")
            yield document
    except YAMLError as e:  # pyre-ignore[66]
        # Remove ruamel usage pointer (see github issue 436)
        if hasattr(e, 'note') and isinstance(e.note, str) and "suppress this check" in e.note:
            e.note = ""
        # TODO: Better error. See also get_asset_content
        raise NotAnAssetError(f"Invalid YAML:\n{str(e)}") from e


def get_temp_file(suffix='.yaml') -> Path:
    r"""Return the Path of a new temporary file.

    Parameters
    ----------
    suffix
        String to append to the filename. Passed to :py:func:`tempfile.mkstemp`.
    """

    from tempfile import mkstemp
    fd, file = mkstemp(prefix='onyo_', suffix=suffix, text=True)

    # close the file descriptor; we don't need it
    os.close(fd)

    return Path(file)


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
        try:
            get_patched_yaml().load(asset)
        except scanner.ScannerError:  # pyre-ignore[66]
            invalid_yaml.append(str(asset))

    if invalid_yaml:
        ui.error('The following files fail YAML validation:\n{}'.format(
            '\n'.join(invalid_yaml)))
        return False

    return True


def write_asset_to_file(asset: Item,
                        path: Path | None = None) -> None:
    r"""Write asset content to a file.

    Pseudokeys are not included in the written YAML.

    Parameters
    ----------
    asset
        Item to write to disk.
    path
        The Path to write content to. Default is the asset's ``'onyo.path.file'``
        pseudokey.
    """

    # TODO: This assumes that `repo` is always set in Item(). This is not yet true, but one day will be.
    path = asset.repo.git.root / asset.get('onyo.path.file') if path is None else path  # pyre-ignore[16]
    path.write_text(asset.yaml())
