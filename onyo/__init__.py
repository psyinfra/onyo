from os.path import join as opj, exists as ope
from pathlib import Path
import logging

class Configuration:
    def __init__(self):
        self._home = str(Path.home())
        self._onyo_dir = opj(self._home, '.onyo')

logging.basicConfig(level=logging.ERROR)  # external logging level
logger = logging.getLogger('onyo')  # internal logging level
logger.setLevel(level=logging.INFO)

__params__ = Configuration()
__all__ = ['logger', '__version__', '__params__']

