from __future__ import annotations


class UIInputError(Exception):
    r"""Raise if UI failed when trying to read input."""


class OnyoCLIExitCode(Exception):
    r"""Raise if the Onyo CLI should exit with a specific value."""
    def __init__(self,
                 message: str,
                 returncode: int):
        self.message = message
        self.returncode = returncode


class OnyoRepoError(Exception):
    r"""Raise if something is wrong with an Onyo repository."""


class OnyoInvalidRepoError(OnyoRepoError):
    r"""Raise if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    r"""Raise if path is protected.

    For example: ``.git/``, :py:data:`onyo.lib.onyo.OnyoRepo.ANCHOR_FILE_NAME`,
    :py:data:`onyo.lib.onyo.OnyoRepo.ONYO_DIR`, etc.
    """


class OnyoInvalidFilterError(Exception):
    r"""Raise if filters are invalidly defined."""


class InvalidArgumentError(Exception):
    r"""Raise if a (CLI-) command is invalidly called beyond what's covered by argparse."""


class InvalidAssetError(Exception):
    r"""Raise if an asset is invalid."""


class InventoryOperationError(Exception):
    r"""Raise if an inventory operation cannot be executed."""


class InvalidInventoryOperationError(InventoryOperationError):
    r"""Raise if an invalid inventory operation is requested."""


class InventoryDirNotEmpty(InvalidInventoryOperationError):
    r"""Raise if an inventory directory is not empty but needs to be in order to perform an operation."""


class PendingInventoryOperationError(InventoryOperationError):
    r"""Raise if there are unexpected pending operations."""
    # TODO  -> enhance message w/ hint to Inventory.reset/commit?
    #          would be useful in python context only


class NoopError(InventoryOperationError):
    r"""Raise if a requested operation is a no-op.

    Signal that an inventory operation would not result in a change, allowing
    callers to determine the failure paradigm: state (already-fine; success) vs
    task (can't-do; failure).
    """


class NotAnAssetError(Exception):
    r"""Raise if an object is expected to be an asset but is not."""


class NotADirError(Exception):
    r"""Raise if an object is expected to be a directory but is not."""
