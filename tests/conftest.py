import shutil
import pytest


@pytest.fixture(scope="session", autouse=True)
def clean_sandbox(request):
    """
    Ensure that 'tests/sandbox' is clean, and doesn't have remnants from
    previous runs.
    """
    sandbox_dir = 'tests/sandbox/'
    shutil.rmtree(sandbox_dir)
