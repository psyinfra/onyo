from __future__ import annotations


class OnyoRepoError(Exception):
    r"""Thrown if something is wrong with an onyo repository."""


class OnyoInvalidRepoError(OnyoRepoError):
    r"""Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    r"""Thrown if path is protected (.anchor, .git/, .onyo/)."""


class OnyoInvalidFilterError(Exception):
    r"""Raise if filters are invalidly defined"""


class InventoryOperationError(Exception):
    r"""Thrown if an inventory operation cannot be executed."""


class InvalidInventoryOperationError(InventoryOperationError):
    r"""Thrown if an invalid inventory operation is requested."""


class PendingInventoryOperationError(InventoryOperationError):
    r"""Thrown if there are unexpected pending operations."""
    # TODO  -> enhance message w/ hint to Inventory.reset/commit?
    #          would be useful in python context only


class NoopError(InventoryOperationError):
    r"""Thrown if a requested operation is a Noop."""
    # This is intended to signal that an inventory operation would not result in any change, so that callers can decide
    # on their failure paradigm:
    # "Result oriented already-fine-no-failure" vs "Task oriented can't-do-failure".


class NotAnAssetError(Exception):
    r"""Thrown if an object was expected to be an asset but isn't"""


class NotADirError(Exception):
    r"""Thrown if an object was expected to be a directory but isn't"""
