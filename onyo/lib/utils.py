from __future__ import annotations

import os
from collections import UserDict
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import CommentedMap, scanner, YAML  # pyre-ignore[21]
from ruamel.yaml.error import YAMLError  # pyre-ignore[21]

from onyo.lib.exceptions import NotAnAssetError
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Any,
        Dict,
        Generator,
        Mapping,
        TypeVar,
    )
    from onyo.lib.items import Item

    _KT = TypeVar("_KT")  # Key type
    _VT = TypeVar("_VT")  # Value type


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


class DotNotationWrapper(UserDict):
    """Access nested dictionaries via hierarchical keys.

    Wrap a dictionary to traverse multidimensional dictionaries using a dot as
    the delimiter. In other words, it provides a view of the flattened
    dictionary::

      > d = {'key': 'value', 'nested': {'key': 'another value'}}
      > wrapper = DotNotationWrapper(d)
      > wrapper['nested.key']
      'another value'
      > list(wrapper.keys())
      ['key', 'nested.key']

    Iteration only considers the flattened view. Keys that contain a dictionary
    are not yielded when using ``.keys()``, ``.values()``, and ``.items()``.

    The underlying dictionary is available via the ``.data`` attribute when the
    standard Python behavior is needed.
    """

    def __init__(self,
                 __dict: Mapping[_KT, _VT] | None = None,
                 pristine_original: bool = True,
                 **kwargs: _VT) -> None:
        r"""Initialize a dot notation wrapped dictionary.

        Parameters
        ----------
        __dict
            Dictionary to wrap.
        pristine_original
            Store ``__dict`` unaltered in the ``.data`` attribute.
            This behavior is the primary intended use for the wrapper: just a
            namespace wrapper for dicts.

            Set to ``False`` to interpret the incoming dict's keys for dot
            notation and set accordingly.
        """

        if pristine_original and __dict and isinstance(__dict, dict):
            # Maintain the original dict object (and class).
            # NOTE: Would modify wrapped dict w/ kwargs if both are given.
            #       deepcopy would prevent this, but contradicts the idea of wrapping.
            super().__init__()
            self.data = __dict
            self.update(**kwargs)
        else:
            # Resort to `UserDict` behavior.
            super().__init__(__dict, **kwargs)

    def _keys(self) -> Generator[str, None, None]:
        """Yield all keys recursively from nested dictionaries in dot notation.

        A by-product of dot notation is that all keys are strings, regardless of
        their original type in the underlying dictionary.

        Keys that contain a dictionary not yielded.
        """

        def recursive_keys(d: dict):
            for k in d.keys():
                if hasattr(d[k], "keys"):
                    yield from (k + "." + sk for sk in recursive_keys(d[k]))
                else:
                    # Cast as a string. One can't have a key 'some.1.more',
                    # where 1 remains an integer.
                    yield str(k)

        yield from recursive_keys(self.data)

    def __getitem__(self,
                    key: _KT) -> Any:
        r"""Get the value of a key."""

        if isinstance(key, str):
            parts = key.split('.')
            effective_dict = self.data
            if len(parts) > 1:
                for lvl in range(len(parts) - 1):
                    try:
                        effective_dict = effective_dict[parts[lvl]]
                    except KeyError as e:
                        raise KeyError(f"'{'.'.join(parts[:lvl + 1])}'") from e
                    except TypeError as e:
                        raise KeyError(f"'{'.'.join(parts[:lvl])}' is not a dictionary.") from e

            try:
                return effective_dict[parts[-1]]
            except KeyError as e:
                raise KeyError(f"'{key}'") from e
            except TypeError as e:
                raise KeyError(f"'{'.'.join(parts[:-1])}' is not a dictionary.") from e

        return super().__getitem__(key)

    def __setitem__(self,
                    key: _KT,
                    item: _VT) -> None:
        r"""Set a key.

        Keys that are strings are interpreted for dot notation, and intermediate
        dictionaries are created as needed.
        """

        if isinstance(key, str):
            parts = key.split('.')
            effective_dict = self.data
            if len(parts) > 1:
                for lvl in range(len(parts) - 1):
                    try:
                        effective_dict = effective_dict[parts[lvl]]
                    except KeyError:
                        # nested dict doesn't exist yet
                        effective_dict[parts[lvl]] = dict()
                        effective_dict = effective_dict[parts[lvl]]

            effective_dict[parts[-1]] = item
        else:
            super().__setitem__(key, item)

    def __delitem__(self,
                    key: _KT) -> None:
        r"""Remove a ``key`` from self."""

        if isinstance(key, str):
            parts = key.split('.')
            effective_dict = self.data
            if len(parts) > 1:
                for lvl in range(len(parts) - 1):
                    try:
                        effective_dict = effective_dict[parts[lvl]]
                    except KeyError as e:
                        raise KeyError(f"'{'.'.join(parts[:lvl + 1])}'") from e
            del effective_dict[parts[-1]]
        else:
            super().__delitem__(key)

    def __contains__(self,
                     key: _KT) -> bool:
        """Whether ``key`` is in self.

        Unlike iteration over keys, keys that contain a dictionary are
        matchable and return ``True``.
        """

        try:
            self.__getitem__(key)
            return True
        except KeyError:
            return False

    def __iter__(self) -> Generator[str, None, None]:
        r"""Return the iterator.

        A by-product of dot notation is that all keys are strings, regardless of
        their original type in the underlying dictionary.

        Keys that contain a dictionary are not yielded.
        """

        return self._keys()

    def __len__(self) -> int:
        r"""Return the number of keys in the dot notation view.

        Keys that contain a dictionary are not counted.
        """

        return len(list(self._keys()))


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


def yaml_to_dict_multi(stream: Path | str) -> Generator[dict | CommentedMap, None, None]:  # pyre-ignore[11]
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

    path = asset.repo.git.root / asset.get('onyo.path.file') if path is None else path
    path.write_text(asset.yaml())
