from collections import UserDict
from pathlib import Path
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

UNSET_VALUE = '<unset>'
r"""Type-symbol for unset keys.

Use for type matching (:py:func:`onyo_get`) and output.
"""

TYPE_SYMBOL_MAPPING = {"<dict>": (dict, UserDict),
                       "<list>": list}
r"""Mapping of Onyo type-symbols with Python types.

Use for type matching (:py:func:`onyo_get`) and output.
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
