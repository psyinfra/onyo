import os
import shutil
import subprocess
from collections.abc import Iterable
from itertools import chain, combinations
from pathlib import Path
from tempfile import gettempdir

from onyo import commands  # noqa: F401
from onyo.lib import Repo
import pytest


@pytest.fixture(scope="function", autouse=True)
def change_cwd_to_sandbox(request, monkeypatch):
    """
    Change the working directory to a "sandbox" that allows tests to run in
    isolation, and not conflict with other tests.

    This is located under /tmp in order to run isolated from the source git
    repository (as the parent dirs are searched for a valid git repo).

    The directory is named "/tmp/onyo-sandbox/<test-file-name>/".
    For example: "/tmp/onyo-sandbox/test_mkdir.py/"

    If the directory does not exist, it will be created.
    """
    tmp = gettempdir()
    sandbox_test_dir = Path(tmp, 'onyo-sandbox', request.path.name)

    # create the dir
    sandbox_test_dir.mkdir(parents=True, exist_ok=True)
    # cd
    monkeypatch.chdir(sandbox_test_dir)


@pytest.fixture(scope="function", autouse=True)
def clean_env(request):
    """
    Ensure that $EDITOR is not inherited from the environment or other tests.
    """
    try:
        del os.environ['EDITOR']
    except KeyError:
        pass


@pytest.fixture(scope="session", autouse=True)
def clean_sandboxes(request):
    """
    Ensure that 'tests/sandbox' is clean, and doesn't have remnants from
    previous runs.
    """
    tmp = gettempdir()
    sandbox_test_dir = Path(tmp, 'onyo-sandbox')
    try:
        shutil.rmtree(sandbox_test_dir)
    except FileNotFoundError:
        pass


@pytest.fixture
def helpers():
    return Helpers


class Helpers:
    @staticmethod
    def flatten(xs):
        for x in xs:
            if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
                yield from Helpers.flatten(x)
            else:
                yield x

    @staticmethod
    def onyo_flags():
        return [['-d', '--debug'],
                [['-C', '/tmp'], ['--onyopath', '/tmp']],
                ]

    @staticmethod
    def powerset(iterable):
        "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

    @staticmethod
    def populate_repo(path: str, dirs: list = [], files: list = []) -> None:
        """
        Create and initialize a folder, and build a directory and file
        structure.
        """
        # setup repo
        ret = subprocess.run(['onyo', 'init', path])
        assert ret.returncode == 0
        repo = Repo(path)

        # dirs
        if dirs:
            repo.mkdir(dirs)

        # files
        if files:
            for i in files:
                Path(path, i).touch()

            repo.add(files)
            repo.commit('populated for tests', files)
