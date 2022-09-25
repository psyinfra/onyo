import os
from pathlib import Path
import logging
from onyo._version import __version__


class Configuration:
    def __init__(self):
        self._home = str(Path.home())
        self._onyo_dir = os.path.join(self._home, '.onyo')


logging.basicConfig(level=logging.ERROR)  # external logging level
logger = logging.getLogger('onyo')  # internal logging level
logger.setLevel(level=logging.INFO)

__params__ = Configuration()
__all__ = ['logger', '__version__', '__params__']
