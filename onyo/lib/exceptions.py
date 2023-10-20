from __future__ import annotations


class OnyoInvalidRepoError(Exception):
    """Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    """Thrown if path is protected (.anchor, .git/, .onyo/)."""


class OnyoInvalidFilterError(Exception):
    """Raise if filters are invalidly defined"""


class InvalidInventoryOperation(Exception):
    """TODO  -> enhance message w/ hint to Inventory.reset/commit"""


class NoopError(Exception):
    """Thrown if a requested operation is a Noop."""


class NotAnAssetError(Exception):
    """Thrown if an object was expected to be an asset but isn't"""
