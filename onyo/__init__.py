import logging
from onyo._version import __version__


logging.basicConfig(level=logging.ERROR)  # external logging level
log = logging.getLogger('onyo')  # internal logging level
log.setLevel(level=logging.INFO)

__all__ = ['log', '__version__']
