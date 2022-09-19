import os
from pathlib import Path
import logging
from onyo._version import __version__

# Load coverage to enable tracking sub-processes for code coverage.
#
# A simple example:
# COVERAGE_PROCESS_START=.coveragerc pytest --cov -vv .
#
# Onyo's tests execute in different working directories, so a more complicated
# invocation is required. See the README or CI config for the right method.
#
# For more information, see
# https://coverage.readthedocs.io/en/latest/subprocess.html
if 'COVERAGE_PROCESS_START' in os.environ:
    import coverage
    coverage.process_startup()


class Configuration:
    def __init__(self):
        self._home = str(Path.home())
        self._onyo_dir = os.path.join(self._home, '.onyo')


logging.basicConfig(level=logging.ERROR)  # external logging level
logger = logging.getLogger('onyo')  # internal logging level
logger.setLevel(level=logging.INFO)

__params__ = Configuration()
__all__ = ['logger', '__version__', '__params__']
