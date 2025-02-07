from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from contextlib import contextmanager
from itertools import chain, combinations
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _pytest.mark.structures import MarkDecorator
from faker.providers import python

from onyo.lib.git import GitRepo
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.lib.items import Item

if TYPE_CHECKING:
    from typing import (
        Generator,
        List,
        Type,
    )


def params(d: dict) -> MarkDecorator:
    r"""
    Parameterizes a dictionary of the form:
    {
        "<ids>": {"variant": <variable>},
        ...
    }
    to run tests with a variable `variant` with the value <variable> and
    <ids> as the test ID.
    """
    return pytest.mark.parametrize(
        argnames=(argnames := sorted({k for v in d.values() for k in v.keys()})),
        argvalues=[[v.get(k) for k in argnames] for v in d.values()],
        ids=d.keys(),
    )


# TODO: - This should get content specification  (worktree vs committed??)
#       - Have the yielded object provide info for assertions
#       - what is/isn't an asset?
#       - asset content specified and accessible as dict
#       - other file content as string
#       - we'd want that for GitRepo, OnyoRepo, Inventory. How?

class AnnotatedGitRepo(GitRepo):

    def __init__(self, path: Path, find_root: bool = False) -> None:
        super().__init__(path, find_root)
        self.test_annotation = None


class AnnotatedOnyoRepo(OnyoRepo):

    def __init__(self, path: Path, init: bool = False, find_root: bool = False) -> None:
        super().__init__(path, init, find_root)
        self.test_annotation = None


@pytest.fixture(scope='function')
def gitrepo(tmp_path: Path, request) -> Generator[AnnotatedGitRepo, None, None]:
    subprocess.run(['git', 'init', str(tmp_path)])
    gr = AnnotatedGitRepo(tmp_path)
    gr.test_annotation = {'files': [],
                          'directories': []}
    m = request.node.get_closest_marker('gitrepo_contents')
    if m:
        for spec in list(m.args):
            path = spec[0]
            content = spec[1]
            abs_path = (tmp_path / path)
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content)
            # TODO: Figure out what's needed for annotation.
            #       Including: paths absolute/relative?
            gr.test_annotation['files'].append(abs_path)
            gr.test_annotation['directories'].extend(gr.root / p for p in path.parents
                                                     if p != Path('.'))
        subprocess.run(['git', 'add', '.'], cwd=gr.root)  # leave .gitignored stuff uncommitted
        subprocess.run(['git', 'commit', '-m', 'Test repo setup'], cwd=gr.root)
    yield gr


@pytest.fixture(scope='function')
def onyorepo(gitrepo, request, monkeypatch) -> Generator[AnnotatedOnyoRepo, None, None]:
    from onyo.lib.utils import deduplicate
    onyo = AnnotatedOnyoRepo(gitrepo.root, init=True)
    onyo.test_annotation = {'assets': [],
                            'dirs': [],
                            'templates': [gitrepo.root / OnyoRepo.TEMPLATE_DIR / "empty",
                                          gitrepo.root / OnyoRepo.TEMPLATE_DIR / "laptop.example"],
                            'git': gitrepo}

    to_commit = []
    m = request.node.get_closest_marker('inventory_assets')
    if m:
        for spec in list(m.args):
            spec['onyo.path.absolute'] = gitrepo.root / spec['onyo.path.relative']
            implicit_dirs = [d for d in spec['onyo.path.absolute'].parents
                             if d.is_relative_to(gitrepo.root)]
            if spec.get('onyo.is.directory'):
                implicit_dirs.append(spec['onyo.path.absolute'])
            to_commit += onyo.mk_inventory_dirs(implicit_dirs)
            onyo.test_annotation['dirs'].extend(implicit_dirs)
            onyo.write_asset_content(spec)
            onyo.test_annotation['assets'].append(spec)
            to_commit.append(spec['onyo.path.absolute'])

    m = request.node.get_closest_marker('inventory_dirs')
    if m:
        dirs = [gitrepo.root / p for p in list(m.args)]
        new_anchors = onyo.mk_inventory_dirs(dirs)
        to_commit += new_anchors
        onyo.test_annotation['dirs'].extend(p.parent for p in new_anchors)

    m = request.node.get_closest_marker('inventory_templates')
    if m:
        for spec in list(m.args):
            path = spec[0]
            content = spec[1]
            abs_path = gitrepo.root / path
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content)
            onyo.test_annotation['templates'].append(abs_path)
            to_commit.append(abs_path)

    if onyo.test_annotation['dirs']:
        onyo.test_annotation['dirs'] = deduplicate(onyo.test_annotation['dirs'])
    if to_commit:
        onyo.commit(deduplicate(to_commit), "onyorepo: setup")  # pyre-ignore[6] - not None if `to_commit` is not None

    # cd into repo; to ease testing
    monkeypatch.chdir(gitrepo.root)
    yield onyo


@pytest.fixture(scope='function')
def repo(tmp_path: Path, monkeypatch, request) -> Generator[OnyoRepo, None, None]:
    r"""
    This fixture:
    - creates a new repository in a temporary directory
    - `cd`s into the repository
    - returns a handle to the repo

    Furthermore, it will populate the repository using these markers:
    - repo_dirs()
    - repo_files()
      - parent directories of files are automatically created
    """
    repo_path = tmp_path
    dirs = set()
    files = set()
    contents = list()

    # initialize repo
    repo_ = OnyoRepo(repo_path, init=True)
    repo_.set_config("onyo.assets.name-format", "{type}_{make}_{model.name}.{serial}")
    repo_.git.commit(repo_.git.root / repo_.ONYO_CONFIG, message="Asset name config w/ dot")
    # collect files to populate the repo
    m = request.node.get_closest_marker('repo_files')
    if m:
        files = {(repo_path / x) for x in m.args}

    # collect dirs to populate the repo
    m = request.node.get_closest_marker('repo_dirs')
    if m:
        dirs = set(m.args)

    # collect contents to populate the repo
    m = request.node.get_closest_marker('repo_contents')
    if m:
        contents = list(m.args)

    # collect files from contents list too
    files |= {(repo_path / x[0]) for x in contents}

    # collect dirs from files list too
    dirs |= {x.parent for x in files if not x.parent.exists()}

    # populate the repo
    if dirs:
        anchors = repo_.mk_inventory_dirs([repo_path / d for d in dirs])
        repo_.commit(paths=anchors,
                     message="populate dirs for tests")

    for i in files:
        i.touch()

    if files:
        if contents:
            for file in contents:
                (repo_path / file[0]).write_text(file[1])
        repo_.commit(paths=files,
                     message="populate files for tests")

    # TODO: Do we still need/want that? CWD should only ever be relevant for CLI tests.
    #       Hence, should probably be done there.
    # cd into repo; to ease testing
    monkeypatch.chdir(repo_path)

    # hand it off
    yield repo_


@pytest.fixture(scope="function")
def inventory(repo) -> Generator:
    # TODO: This is currently not in line with `repo`, where files and dirs are defined differently.
    #       Paths to created items should be delivered somehow.
    inventory = Inventory(repo=repo)
    inventory.add_asset(Item(
        dict(some_key="some_value",
             type="TYPE",
             make="MAKER",
             model=dict(name="MODEL"),
             serial="SERIAL",
             other=1,
             directory=repo.git.root / "somewhere" / "nested"),
        repo=repo))
    inventory.add_directory(repo.git.root / 'empty')
    inventory.add_directory(repo.git.root / 'different' / 'place')
    inventory.commit("First asset added")
    yield inventory


@pytest.fixture(scope="function", autouse=True)
def clean_env(request) -> None:
    r"""
    Ensure that $EDITOR is not inherited from the environment or other tests.
    """
    try:
        del os.environ['EDITOR']
    except KeyError:
        pass


class Helpers:
    @staticmethod
    def flatten(xs):
        for x in xs:
            if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
                yield from Helpers.flatten(x)
            else:
                yield x

    @staticmethod
    def onyo_flags() -> List[List[List[str]] | List[str]]:
        return [['-d', '--debug'],
                [['-C', '/tmp'], ['--onyopath', '/tmp']],
                ]

    @staticmethod
    def powerset(iterable: Iterable):
        "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


@pytest.fixture
def helpers() -> Type[Helpers]:
    return Helpers


@pytest.fixture(scope='function', autouse=True)
def set_ui_function(request) -> None:
    r"""Set up onyo.lib.ui according to a dict provided by the 'ui' marker"""
    from onyo.lib.ui import ui
    m = request.node.get_closest_marker('ui')
    if m:
        ui.set_yes(m.args[0].get('yes', False))
        ui.set_quiet(m.args[0].get('quiet', False))
        ui.set_debug(m.args[0].get('debug', False))

@pytest.fixture(scope='class', autouse=True)
def set_ui_class(request) -> None:
    r"""Set up onyo.lib.ui according to a dict provided by the 'ui' marker"""
    from onyo.lib.ui import ui
    m = request.node.get_closest_marker('ui')
    if m:
        ui.set_yes(m.args[0].get('yes', False))
        ui.set_quiet(m.args[0].get('quiet', False))
        ui.set_debug(m.args[0].get('debug', False))


class OnyoProvider(python.Provider):
    r"""
    Faker Provider for Onyo.
    """
    def onyo_asset_dicts(self,
                         num: int = 1,
                         override: dict | None = None) -> Generator[dict, None, None]:
        r"""
        Yield asset dictionaries suitable for populating realistic assets.
        """
        if override is None:
            override = {}

        for _ in range(num):
            yield {
                'type': next(self.onyo_types()),
                'make': next(self.onyo_manufacturers()),
                'model': { 'name': self.numerify(text='Wizbang %##!') },
                'serial': self.pystr(min_chars=15),
                'keyboard': next(self.onyo_keyboards()),
                'display': {
                    'size': self.numerify(text='%#'),
                    'resolution': self.numerify(text='%##! x %##!'),
                    'hz': self.numerify(text='%#!'),
                },
                'RAM': self.numerify(text='%#!!G'),
                'CPU': {
                    'vendor': next(self.onyo_cpu_vendors()),
                    'cores': self.numerify(text='%#!'),
                    'arch': next(self.onyo_cpu_archs()),
                    'model': self.numerify(text='Speedy % %%##Z'),
                },
                'disk': { 'size': self.numerify(text='%#!T') },
            } | override


    def onyo_cpu_archs(self,
                       num: int = 1) -> Generator[str, None, None]:
        r"""
        Yield CPU architectures.
        """
        cpu_archs = (
            'aarch64',
            'amd64',
            'ppc64',
            'x86',
        )
        yield self.random_element(elements=cpu_archs)


    def onyo_cpu_vendors(self,
                         num: int = 1) -> Generator[str, None, None]:
        r"""
        Yield CPU vendors.
        """
        cpu_vendors = (
            'amd',
            'apple',
            'intel',
            'ibm',
        )
        yield self.random_element(elements=cpu_vendors)


    def onyo_directories(self,
                         num: int = 1) -> Generator[str, None, None]:
        r"""
        Yield directory names.

        Useful for ``onyo.path.directory``.
        """
        locations = (
            'repair',
            'shelf',
            'warehouse',
            'group',
            'group/Accounting',
            'group/Creative',
            'group/HR',
            'group/IT',
            'group/Operations',
            'group/Purchasing',
            'group/Sales',
        )
        for _ in range(num):
            yield self.random_element(elements=locations)


    def onyo_keyboards(self,
                       num: int = 1) -> Generator[str, None, None]:
        r"""
        Yield keyboard layout names.
        """
        keyboards = (
            'azerty',
            'qwerty',
            'qwertz',
            'qzerty',
            'qüerty',
            'ąžerty',
        )
        yield self.random_element(elements=keyboards)


    def onyo_manufacturers(self,
                           num: int = 1) -> Generator[str, None, None]:
        r"""
        Yield manufacturers.
        """
        manufacturers = (
            'apple',
            'asus',
            'cisco',
            'dell',
            'eizo',
            'framework',
            'hp',
            'lenovo',
            'samsung',
            'sun',
            'toshiba',
            'zebra',
        )
        yield self.random_element(elements=manufacturers)


    def onyo_types(self,
                   num: int = 1) -> Generator[str, None, None]:
        r"""
        Yield asset types.
        """
        types = (
            'desktop',
            'display',
            'laptop',
            'pdu',
            'server',
            'switch',
            'ups',
        )
        yield self.random_element(elements=types)


@pytest.fixture(scope="session")
def fixture_fake() -> Generator:
    r"""
    Yield a faker object with the Onyo Provider loaded.

    Onyo-specific functions are all prefixed with ``onyo_``.
    """
    from faker import Faker

    _fake = Faker()
    _fake.add_provider(OnyoProvider)
    yield _fake


@contextmanager
def _context_for_fixture(val_to_yield_after_setup):
    yield val_to_yield_after_setup


@pytest.fixture(scope='function', name='fake')
def fake_function_scope(fixture_fake):
    with _context_for_fixture(fixture_fake) as result:
        yield result


@pytest.fixture(scope='class')
def fake_class_scope(fixture_fake):
    with _context_for_fixture(fixture_fake) as result:
        yield result


@pytest.fixture(scope='module')
def fake_module_scope(fixture_fake):
    with _context_for_fixture(fixture_fake) as result:
        yield result


@pytest.fixture(scope='session')
def fake_session_scope(fixture_fake):
    with _context_for_fixture(fixture_fake) as result:
        yield result
