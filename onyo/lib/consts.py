from collections import UserDict
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
