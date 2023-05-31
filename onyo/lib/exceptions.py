from __future__ import annotations


class OnyoInvalidRepoError(Exception):
    """Thrown if the repository is invalid."""


class OnyoProtectedPathError(Exception):
    """Thrown if path is protected (.anchor, .git/, .onyo/)."""


class OnyoInvalidFilterError(Exception):
    """Raise if filters are invalidly defined"""
