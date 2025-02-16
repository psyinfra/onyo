from __future__ import annotations

import copy
from collections import UserDict
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import CommentedMap, scanner, YAML  # pyre-ignore[21]
from ruamel.yaml.error import YAMLError  # pyre-ignore[21]
from ruamel.yaml.representer import RoundTripRepresenter  # pyre-ignore[21]
from ruamel.yaml.dumper import RoundTripDumper  # pyre-ignore[21]

from onyo.lib.consts import RESERVED_KEYS
from onyo.lib.pseudokeys import PSEUDO_KEYS, PseudoKey
from onyo.lib.exceptions import NotAnAssetError
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Any,
        Dict,
        Generator,
        Hashable,
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
    yaml.resolver.add_implicit_resolver(tag="tag:yaml.org,2002:null",
                                        regexp=RegExp('''^(?: ~
                                                      |null|Null|NULL
                                                      | )$''', re.X),
                                        first=['~', 'n', 'N', ''])
    # everything else is a string
    yaml.resolver.add_implicit_resolver(tag="tag:yaml.org,2002:str",
                                        regexp=RegExp('^.*$'),
                                        first=None)

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
                        raise TypeError(f"'{'.'.join(parts[:lvl])}' is not a dictionary.") from e

            try:
                return effective_dict[parts[-1]]
            except KeyError as e:
                raise KeyError(f"'{key}'") from e
            except TypeError as e:
                raise TypeError(f"'{'.'.join(parts[:-1])}' is not a dictionary.") from e

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


def dict_to_asset_yaml(d: Dict | UserDict) -> str:
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
    for key in RESERVED_KEYS + list(PSEUDO_KEYS.keys()):
        if key in content:
            del content[key]

    # Empty dicts are serialized to '{}', and I was unable to find any input
    # ('', None, etc) that would serialize to nothing. Hardcoding, though ugly,
    # seems to be the only option.
    if not content:
        return '---\n'

    from io import StringIO
    yaml = get_patched_yaml()
    yaml.explicit_start = True
    s = StringIO()
    yaml.dump(content.data
              if isinstance(content, DotNotationWrapper)
              else content,
              s)

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

    yaml = get_patched_yaml()
    contents = dict()
    try:
        contents = yaml.load(asset_file)
    except YAMLError as e:  # pyre-ignore[66]
        # Remove ruamel usage pointer (see github issue 436)
        if hasattr(e, 'note') and isinstance(e.note, str) and "suppress this check" in e.note:
            e.note = ""
        raise NotAnAssetError(f"Invalid YAML in {asset_file}:\n{str(e)}") from e

    if contents is None:
        return dict()

    if not isinstance(contents, (dict, CommentedMap)):
        # For example: a simple text file may technically be valid YAML,
        # but we may get a string instead of dict.
        raise NotAnAssetError(f"{asset_file} does not appear to be an asset.")

    return contents


def get_temp_file() -> Path:
    r"""Return the Path of a new temporary file."""

    from tempfile import mkstemp
    fd, tmp_path = mkstemp(prefix='onyo_', suffix='.yaml', text=True)

    return Path(tmp_path)


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


def write_asset_file(path: Path,
                     asset: Dict | UserDict) -> None:
    r"""Write content to an asset file.

    All ``RESERVED_KEYS`` will be stripped from the content before writing.

    Parameters
    ----------
    path
        The Path to write content to.
    asset
        A dictionary of content to write to the path.
    """

    # TODO: Get file path from onyo.path.file?
    path.open('w').write(dict_to_asset_yaml(asset))


class YAMLDumpWrapper(UserDict):
    r"""Wrapper class to access ruamel's representation of data.

    This addresses the issue that ``serial: 001234`` yields ``{'serial': 1234}``,
    but is dumped as ``serial: 001234``, interfering with comparisons assessing
    whether there's a modification.
    """

    def __init__(self,
                 d: dict | UserDict):
        r"""Initialize a YAMLDumpWrapper."""

        super().__init__(d)

    def __getitem__(self,
                    item: Hashable):
        r"""Get the value of a key."""

        data = self.data[item]  # potentially raises KeyError
        if isinstance(data, dict) and data:
            # non-empty dict: recurse
            return YAMLDumpWrapper(data)
        if isinstance(data, list) and data:
            # non-empty list: Implement analogous wrapper
            raise NotImplementedError
        if isinstance(data, (Path, PseudoKey)):
            return data  # no representer for `Path` and `PseudoKey`

        return RoundTripRepresenter(dumper=RoundTripDumper(stream=StringIO())).represent_data(data).value


def is_equal_assets_dict(a: Item,
                         b: Item) -> bool:
    r"""Whether two Items have the same content and comments."""

    # TODO: This entire function may become part of the Item class instead (__eq__?)

    # Note: Checking types here, because of potential recursive calls.
    if not isinstance(a, (dict, UserDict)) or not isinstance(b, (dict, UserDict)):
        return False

    if isinstance(a, DotNotationWrapper):
        a = a.data
    if isinstance(b, DotNotationWrapper):
        b = b.data

    # TODO: Problem:
    #   In test_edit_single_asset second invocation of edit, is_equal_asset_dict comparison returns False
    #   for the wrong reason (unresolved `PseudoKey` instance, b/c we were looking at the python dict, not the Item.)
    #   While the trigger is fixed, this is still wrong in this recursion here:

    # Recurse into nested dicts:
    for k, v in a.items():
        if isinstance(v, (dict, UserDict)):
            try:
                eq_ = is_equal_assets_dict(a[k], b[k])
            except (KeyError, TypeError):
                eq_ = False
            if not eq_:
                return False

    if not isinstance(a, CommentedMap) and not isinstance(b, CommentedMap):
        return a == b

    if YAMLDumpWrapper(a) != YAMLDumpWrapper(b):
        # not accounting for comments yet
        return False

    # The ruamel implementation of `__eq__` and `__contains__` breaks when
    # comparing across files, because the `start_mark` attribute of a
    # `CommentToken` is a `FileMark` that holds the path of the file the content
    # was read from.
    # Thus, our own comparison, ignoring the path.
    from ruamel.yaml.comments import Comment, comment_attrib  # pyre-ignore[21]
    from ruamel.yaml import CommentToken
    a_comment = getattr(a, comment_attrib, Comment())
    b_comment = getattr(b, comment_attrib, Comment())

    def contains_all_comments(container: Comment,
                              comment: Comment) -> bool:  # pyre-ignore[11]
        for a_key, a_values in comment.items.items():
            try:
                b_values = container.items.get(a_key)
            except KeyError:
                # `a` has an annotation at a key that's not in `b`'s annotations
                return False
            if not b_values:
                return False
            if len(a_values) != len(b_values):
                # Not sure whether this is necessary (may be a defined, fixed length),
                # but better be safe.
                return False
            for a_v, b_v in zip(a_values, b_values):
                if type(a_v) is not type(b_v):
                    return False
                if isinstance(a_v, CommentToken) and \
                        (a_v.value, a_v.start_mark.line, a_v.start_mark.column) != \
                        (b_v.value, b_v.start_mark.line, b_v.start_mark.column):
                    return False
        return True

    return contains_all_comments(b_comment, a_comment) and contains_all_comments(a_comment, b_comment)
