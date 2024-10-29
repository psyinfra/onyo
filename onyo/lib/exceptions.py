from __future__ import annotations


class UIInputError(Exception):
    r"""Raised if UI failed when trying to read input"""


class OnyoCLIExitCode(Exception):
    r"""Raised if the onyo CLI should exit with a specific value."""
    def __init__(self,
                 message: str,
                 returncode: int):
        self.message = message
        self.returncode = returncode


class OnyoRepoError(Exception):
    r"""Raised if something is wrong with an Onyo repository."""


class OnyoInvalidRepoError(OnyoRepoError):
    r"""Raised if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    r"""Raised if path is protected (.anchor, .git/, .onyo/)."""


class OnyoInvalidFilterError(Exception):
    r"""Raised if filters are invalidly defined."""


class InvalidArgumentError(Exception):
    r"""Raised a (CLI-) command is invalidly called beyond what's covered by argparse."""


class InventoryOperationError(Exception):
    r"""Raised if an inventory operation cannot be executed."""


class InvalidInventoryOperationError(InventoryOperationError):
    r"""Raised if an invalid inventory operation is requested."""


class InventoryDirNotEmpty(InvalidInventoryOperationError):
    r"""Raised if an inventory directory needs to be empty to perform an operation but is not."""


class PendingInventoryOperationError(InventoryOperationError):
    r"""Raised if there are unexpected pending operations."""
    # TODO  -> enhance message w/ hint to Inventory.reset/commit?
    #          would be useful in python context only


class NoopError(InventoryOperationError):
    r"""Raised if a requested operation is a Noop."""
    # This is intended to signal that an inventory operation would not result in any change, so that callers can decide
    # on their failure paradigm:
    # "Result oriented already-fine-no-failure" vs "Task oriented can't-do-failure".


class NotAnAssetError(Exception):
    r"""Raised if an object is expected to be an asset but is not."""


class NotADirError(Exception):
    r"""Raised if an object is expected to be a directory but is not."""
