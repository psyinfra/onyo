import logging
from onyo._version import __version__
from onyo.lib import (
    Filter, OnyoRepo, OnyoInvalidRepoError,
    OnyoProtectedPathError, OnyoInvalidFilterError)


logging.basicConfig(level=logging.ERROR)  # external logging level
log: logging.Logger = logging.getLogger('onyo')  # internal logging level
log.setLevel(level=logging.INFO)

__all__ = [
    'log',
    '__version__',
    'Filter',
    'OnyoInvalidRepoError',
    'OnyoProtectedPathError',
    'OnyoInvalidFilterError',
    'OnyoRepo',
]
