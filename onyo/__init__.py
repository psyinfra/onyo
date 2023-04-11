import logging
from onyo._version import __version__
from onyo.lib import Repo, OnyoInvalidRepoError, OnyoProtectedPathError


logging.basicConfig(level=logging.ERROR)  # external logging level
log: logging.Logger = logging.getLogger('onyo')  # internal logging level
log.setLevel(level=logging.INFO)

__all__ = [
    'log',
    '__version__',
    'OnyoInvalidRepoError',
    'OnyoProtectedPathError',
    'Repo',
]
