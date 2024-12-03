from collections import UserDict
from typing import TYPE_CHECKING

from onyo.lib.pseudokeys import PSEUDOKEY_ALIASES
if TYPE_CHECKING:
    from typing import Literal
    sort_t = Literal['ascending', 'descending']


RESERVED_KEYS = ['template', 'onyo'] + list(PSEUDOKEY_ALIASES.keys())
# TODO: That's not right yet. We need all aliases and the "onyo." namespace
# How do we deal with namespaces, though? We may want Item/DotNotationWrapper
# to yield views based on namespaces.
r"""Key names that are reserved and must not be part of asset content.

These keys have functional meaning for Onyo. Thus they are reserved and cannot
be part of asset content.
"""
# TODO: other symbols like <list>, <dict>, and potentially <none> or <null>?
UNSET_VALUE = '<unset>'
r"""String to represent keys that are not set.
"""

KNOWN_REPO_VERSIONS = ['1', '2']
r"""Onyo repository versions that this version of onyo knows.

Needed to realize when onyo runs on a repo that was created by a newer version.
(Or a user messed it up).
"""

SORT_ASCENDING = 'ascending'
SORT_DESCENDING = 'descending'

TYPE_SYMBOL_MAPPING = {"<dict>": (dict, UserDict),
                       "<list>": list}
r"""Mapping of symbols for use w/ type matching (`onyo_get`) and simplified output.
"""
