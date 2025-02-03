from collections import UserDict
from typing import TYPE_CHECKING

from onyo.lib.pseudokeys import PSEUDOKEY_ALIASES
if TYPE_CHECKING:
    from typing import Literal
    sort_t = Literal['ascending', 'descending']


RESERVED_KEYS = ['template', 'onyo'] + list(PSEUDOKEY_ALIASES.keys())
# TODO: That's not right yet. We need all aliases and the "onyo." namespace
r"""Key names that are reserved and must not be part of asset content.

These keys have functional meaning for Onyo. Thus they are reserved and cannot
be part of asset content.
"""

KNOWN_REPO_VERSIONS = ['1', '2']
r"""Onyo repository versions that this version of onyo knows.

Needed to realize when onyo runs on a repo that was created by a newer version.
(Or a user messed it up).
"""

SORT_ASCENDING = 'ascending'
r"""Sort ascending.

Used to sort the output of :py:func:`onyo_get`.
"""
SORT_DESCENDING = 'descending'
r"""Sort descending.

Used to sort the output of :py:func:`onyo_get`.
"""

UNSET_VALUE = '<unset>'
r"""String to represent keys that are not set.
"""

TYPE_SYMBOL_MAPPING = {"<dict>": (dict, UserDict),
                       "<list>": list}
r"""Mapping of Onyo type-symbols with Python types.

For use with type matching (:py:func:`onyo_get`) and output.
"""
