from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Literal
    sort_t = Literal['ascending', 'descending']


PSEUDO_KEYS = ['path']
r"""Key names that are addressable but not in asset content.

All ``PSEUDO_KEYS`` are reserved.

See Also
--------
RESERVED_KEYS
"""
RESERVED_KEYS = ['directory', 'is_asset_directory', 'template']
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
