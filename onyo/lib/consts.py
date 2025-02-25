from collections import UserDict
from pathlib import Path
from types import NoneType
from typing import TYPE_CHECKING

from onyo.lib.pseudokeys import PSEUDOKEY_ALIASES

if TYPE_CHECKING:
    from typing import Literal
    sort_t = Literal['ascending', 'descending']


RESERVED_KEYS = ['template', 'onyo'] + list(PSEUDOKEY_ALIASES.keys())
# TODO: That's not right yet. We need all aliases and the "onyo." namespace
r"""Reserved key names that must not be part of asset content.

These keys have functional meaning for Onyo. They are reserved and cannot be
part of asset content.
"""

KNOWN_REPO_VERSIONS = ['1', '2']
r"""Onyo repository versions that this onyo version knows about.

Use for backwards compatibility, upgrades, and detecting repositories created by
a newer version.
"""

SORT_ASCENDING = 'ascending'
r"""Sort ascending.

Use to sort the output of :py:func:`onyo_get`.
"""

SORT_DESCENDING = 'descending'
r"""Sort descending.

Use to sort the output of :py:func:`onyo_get`.
"""

TAG_BOOL = '<bool>'
r"""Tag symbol for keys with a boolean as the value.

Use for type matching (:py:func:`onyo_get`).
"""

TAG_DICT = '<dict>'
r"""Tag symbol for keys with a dict as the value.

Use for type matching (:py:func:`onyo_get`) and output.
"""

TAG_EMPTY = '<empty>'
r"""Tag symbol for keys set to null or are an empty string, dictionary, or list.

Use for type matching (:py:func:`onyo_get`).
"""

TAG_FALSE = '<false>'
r"""Tag symbol for keys with False as the value.

Use for type matching (:py:func:`onyo_get`).
"""

TAG_LIST = '<list>'
r"""Tag symbol for keys with a list as the value.

Use for type matching (:py:func:`onyo_get`) and output.
"""

TAG_NULL = '<null>'
r"""Tag symbol for keys with a null value.

Use for type matching (:py:func:`onyo_get`) and output.
"""

TAG_TRUE = '<true>'
r"""Tag symbol for keys with True as the value.

Use for type matching (:py:func:`onyo_get`).
"""

TAG_UNSET = '<unset>'
r"""Tag symbol for unset keys.

Use for type matching (:py:func:`onyo_get`) and output.
"""

TAG_MAP_TYPES = {
    TAG_BOOL: bool,
    TAG_DICT: (dict, UserDict),
    TAG_LIST: list,
}
r"""Mapping of Onyo type-symbols with Python types.

Use for type matching (:py:func:`onyo_get`) queries.
"""

TAG_MAP_VALUES = {
    TAG_FALSE: False,
    TAG_NULL: None,
    TAG_TRUE: True,
}
r"""Mapping of Onyo value symbols with Python values.

Use for type matching (:py:func:`onyo_get`) queries.
"""

TAG_MAP_OUTPUT = {
    TAG_DICT: (dict, UserDict),
    TAG_LIST: list,
    TAG_NULL: NoneType,
}
r"""Mapping of Onyo types/values for user-oriented output.

Use for :py:func:`onyo_get` output.
"""

ONYO_DIR = Path('.onyo')
r"""The Path of the "dot onyo" directory that contains the onyo configuration, templates, etc."""

ONYO_CONFIG = ONYO_DIR / 'config'
r"""Path of the Onyo config file."""

TEMPLATE_DIR = ONYO_DIR / 'templates'
r"""Path of the directory that stores templates."""

ANCHOR_FILE_NAME = '.anchor'
r"""Name of the empty file created in all directories to "anchor" them.

This is necessary because git only tracks files and not directories.
"""

ASSET_DIR_FILE_NAME = '.onyo-asset-dir'
r"""Name of the file that asset-content is stored in for Asset Directories."""

IGNORE_FILE_NAME = '.onyoignore'
r"""Name of the file that is Onyo's version of Git's ``.gitignore`` file."""
