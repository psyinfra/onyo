import os
from collections.abc import Iterable
from itertools import chain, combinations
from pathlib import Path

from onyo import Repo
import pytest
from typing import List, Type, Union


@pytest.fixture(scope='function')
def repo(tmp_path, monkeypatch, request):
    """
    This fixture:
    - creates a new repository in a temporary directory
    - `cd`s into the repository
    - returns a handle to the repo

    Furthermore, it will populate the repository using these markers:
    - repo_dirs()
    - repo_files()
      - parent directories of files are automatically created
    """
    repo_path = Path(tmp_path)
    dirs = set()
    files = set()
    contents = list()

    # initialize repo
    repo_ = Repo(repo_path, init=True)

    # collect files to populate the repo
    m = request.node.get_closest_marker('repo_files')
    if m:
        files = {Path(repo_path, x) for x in m.args}

    # collect dirs to populate the repo
    m = request.node.get_closest_marker('repo_dirs')
    if m:
        dirs = set(m.args)

    # collect contents to populate the repo
    m = request.node.get_closest_marker('repo_contents')
    if m:
        contents = list(m.args)

    # collect files from contents list too
    files |= {Path(repo_path, x[0]) for x in contents}

    # collect dirs from files list too
    dirs |= {x.parent for x in files if not x.parent.exists()}

    # populate the repo
    if dirs:
        repo_.mkdir(dirs)
        repo_.commit('populate dirs for tests', dirs)

    for i in files:
        i.touch()

    if files:
        if contents:
            for file in contents:
                Path(repo_path, file[0]).write_text(file[1])
        repo_.add(files)
        repo_.commit('populate files for tests', files)

    # cd into repo; to ease testing
    monkeypatch.chdir(repo_path)

    # hand it off
    yield repo_


@pytest.fixture(scope="function", autouse=True)
def clean_env(request) -> None:
    """
    Ensure that $EDITOR is not inherited from the environment or other tests.
    """
    try:
        del os.environ['EDITOR']
    except KeyError:
        pass


@pytest.fixture
def helpers() -> Type[Helpers]:
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
    def onyo_flags() -> List[Union[List[List[str]], List[str]]]:
        return [['-d', '--debug'],
                [['-C', '/tmp'], ['--onyopath', '/tmp']],
                ]

    @staticmethod
    def powerset(iterable):
        "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))
