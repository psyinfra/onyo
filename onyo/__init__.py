import logging
from onyo._version import __version__


logging.basicConfig(level=logging.ERROR)  # external logging level
logger = logging.getLogger('onyo')  # internal logging level
logger.setLevel(level=logging.INFO)

__all__ = ['logger', '__version__']
