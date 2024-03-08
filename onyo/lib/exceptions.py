from __future__ import annotations


class OnyoRepoError(Exception):
    """Thrown if something is wrong with an onyo repository."""


class OnyoInvalidRepoError(OnyoRepoError):
    """Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    """Thrown if path is protected (.anchor, .git/, .onyo/)."""


class OnyoInvalidFilterError(Exception):
    """Raise if filters are invalidly defined"""


class InventoryOperationError(Exception):
    """Thrown if an inventory operation cannot be executed."""


class InvalidInventoryOperationError(InventoryOperationError):
    """Thrown if an invalid inventory operation is requested."""


class PendingInventoryOperationError(InventoryOperationError):
    """Thrown if there are unexpected pending operations."""
    # TODO  -> enhance message w/ hint to Inventory.reset/commit?
    #          would be useful in python context only


class NoopError(InventoryOperationError):
    """Thrown if a requested operation is a Noop."""
    # This is intended to signal that an inventory operation would not result in any change, so that callers can decide
    # on their failure paradigm:
    # "Result oriented already-fine-no-failure" vs "Task oriented can't-do-failure".


class NotAnAssetError(Exception):
    """Thrown if an object was expected to be an asset but isn't"""


class NotADirError(Exception):
    """Thrown if an object was expected to be a directory but isn't"""
