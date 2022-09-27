import os
import shutil
from pathlib import Path
import pytest


@pytest.fixture(scope="function", autouse=True)
def clean_editor(request):
    """
    Ensure that $EDITOR is not inherited from the environment or other tests.
    """
    try:
        del os.environ['EDITOR']
    except KeyError:
        pass


@pytest.fixture(scope="session", autouse=True)
def clean_sandbox(request):
    """
    Ensure that 'tests/sandbox' is clean, and doesn't have remnants from
    previous runs.
    """
    for s in sorted(Path('tests/').glob('**/sandbox')):
        try:
            shutil.rmtree(s)
        except FileNotFoundError:
            pass


@pytest.fixture
def helpers():
    return Helpers


class Helpers:
    @staticmethod
    def string_in_file(string, file):
        """
        Test whether a string is in a file.
        """
        with open(file) as f:
            if string in f.read():
                return True

        return False
