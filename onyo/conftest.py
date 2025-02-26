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

from onyo.lib.faker import OnyoProvider
from onyo.lib.git import GitRepo
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.lib.items import Item

if TYPE_CHECKING:
    from typing import (
        Generator,
        List,
        Tuple,
        Type,
    )


########################################
#
# general
#
########################################
@pytest.fixture(scope="function", autouse=True)
def clean_env(request) -> None:
    r"""Ensure that ``$EDITOR`` is unset.

    Makes sure that the ``$EDITOR`` environment variable is not inherited from
    the user environment nor other tests.
    """

    try:
        del os.environ['EDITOR']
    except KeyError:
        pass


def params(d: dict) -> MarkDecorator:
    r"""Parameterize a dictionary with human-friendly names.

    Allows for meaningful variant names to be printed to the CLI when <variable>
    is not easily string-ify-able.

    For example, to run tests with a variable ``variant`` with the value
    ``<variable>`` and ``<id>`` as the test ID::

      {
          "<id>": {"variant": <variable>},
          ...
      }
    """

    return pytest.mark.parametrize(
        argnames=(argnames := sorted({k for v in d.values() for k in v.keys()})),
        argvalues=[[v.get(k) for k in argnames] for v in d.values()],
        ids=d.keys(),
    )


########################################
#
# tmp_path
#
########################################
@pytest.fixture(scope="class")
def tmp_path_class_scope(tmp_path_factory,
                         request):
    r"""Scope the ``tmp_path`` parameter fixture for classes."""

    yield tmp_path_factory.mktemp(request.node.name)


@pytest.fixture(scope="module")
def tmp_path_module_scope(tmp_path_factory,
                          request):
    r"""Scope the ``tmp_path`` parameter fixture for modules."""

    yield tmp_path_factory.mktemp(request.node.name)


@pytest.fixture(scope="session")
def tmp_path_session_scope(tmp_path_factory,
                           request):
    r"""Scope the ``tmp_path`` parameter fixture for sessions."""

    yield tmp_path_factory.mktemp(request.node.name)


########################################
#
# gitrepo
#
########################################
class AnnotatedGitRepo(GitRepo):
    r"""Annotate a ``GitRepo`` object to ease testing.

    Populated files and directories are stored in ``.test_annotation``.
    """

    def __init__(self,
                 path: Path,
                 find_root: bool = False) -> None:
        r"""Instantiate an ``AnnotatedGitRepo`` object with ``path`` as the root directory.

        Parameters
        ----------
        path
            Absolute Path of a git repository.
        find_root
            Replace ``path`` with the results of :py:func:`onyo.lib.git.GitRepo.find_root`.
            Thus any directory of a git repository can be passed as ``path``,
            not just the repo root.
        """

        super().__init__(path, find_root)
        self.test_annotation = None


@contextmanager
def fixture_gitrepo(tmp_path: Path,
                    request) -> Generator[AnnotatedGitRepo, None, None]:
    r"""Yield an AnnotatedGitRepo object, populated from fixtures.

    A fresh repository is created in a unique temporary directory. It is
    populated via the following marker (which is then stored in
    ``.test_annotation`` for later reference by tests):

    - ``gitrepo_contents()``

    Parent directories of all items are automatically created.

    Example markers::

      gitrepo_contents((Path('.gitignore'), "dir_to_ignore/"),
                       (Path("dir_to_ignore/some.pdf"), "0xDEADBEEF"),
                       (Path("a/b/c/"), ""),
                       (Path("1/2/3/"), ""),
                       )

    Example annotations::

      for dir_path in onyorepo.test_annotation['directories']:
          assert dir_path.is_dir() is True
    """

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


@pytest.fixture(scope='function', name='gitrepo')
def gitrepo_function_scope(tmp_path: Path,
                           request) -> Generator:
    r"""Scope the ``gitrepo`` parameter fixture for functions."""

    with fixture_gitrepo(tmp_path, request) as result:
        yield result


@pytest.fixture(scope='class')
def gitrepo_class_scope(tmp_path_class_scope: Path,
                        request) -> Generator:
    r"""Scope the ``gitrepo`` parameter fixture for classes."""

    with fixture_gitrepo(tmp_path_class_scope, request) as result:
        yield result


@pytest.fixture(scope='module')
def gitrepo_module_scope(tmp_path_module_scope: Path,
                         request) -> Generator:
    r"""Scope the ``gitrepo`` parameter fixture for modules."""

    with fixture_gitrepo(tmp_path_module_scope, request) as result:
        yield result


@pytest.fixture(scope='session')
def gitrepo_session_scope(tmp_path: Path,
                          request) -> Generator:
    r"""Scope the ``gitrepo`` parameter fixture for sessions."""

    with fixture_gitrepo(tmp_path, request) as result:
        yield result


########################################
#
# onyorepo
#
########################################
class AnnotatedOnyoRepo(OnyoRepo):
    r"""Annotate an ``OnyoRepo`` object to ease testing.

    Populated inventory items are stored in ``.test_annotation``.
    """

    def __init__(self,
                 path: Path,
                 init: bool = False,
                 find_root: bool = False) -> None:
        r"""Instantiate an ``AnnotatedOnyoRepo`` object with ``path`` as the root directory.

        Parameters
        ----------
        path
            Absolute path to the root of the Onyo Repository.
        init
            Initialize ``path`` as a git repo and create/populate the subdir
            ``.onyo/``. Cannot be used with ``find_root=True``.
        find_root
            Replace ``path`` with the results of :py:func:`onyo.lib.onyo.OnyoRepo.find_root`.
            Thus any directory of a git repository can be passed as ``path``,
            not just the repo root. Cannot be used with ``init==True``.
        """

        super().__init__(path, init, find_root)
        self.test_annotation = None


@contextmanager
def fixture_onyorepo(gitrepo,
                     request) -> Generator[AnnotatedOnyoRepo, None, None]:
    r"""Yield an AnnotatedOnyoRepo object, populated from fixtures.

    A fresh repository is created in a unique temporary directory. It is
    populated via these markers (which are then stored in ``.test_annotation``
    for later reference by tests):

    - ``inventory_assets()``
    - ``inventory_dirs()``
    - ``inventory_templates()``

    Parent directories of all items are automatically created.

    Example markers::

      inventory_assets()
      inventory_assets(Item(type="type", make="make", model="model", serial=1,
                            onyo.path.parent=Path("here/")),
                       Item(type="type", make="make", model="model", serial=2,
                            onyo.path.parent=Path("there/")),
                       )
      inventory_dirs(Path('a/b/c/'),
                     Path('1/2/3/'),
                     )
      inventory_templates()
      inventory_templates((onyo.lib.consts.TEMPLATE_DIR / "generic" / "laptop",
                           "---\ntype: laptop\n"),
                          (onyo.lib.consts.TEMPLATE_DIR / "generic" / "display",
                           "---\ntype: display\n"),
                          )

    Example annotations::

      for asset_path in onyorepo.test_annotation['assets']:
          assert onyorepo.is_asset_path(asset_path) is True
    """

    from onyo.lib.utils import deduplicate

    onyo = AnnotatedOnyoRepo(gitrepo.root, init=True)
    onyo.test_annotation = {'assets': [],
                            'dirs': [],
                            'templates': [onyo.template_dir / "laptop.example"],
                            'git': gitrepo}

    to_commit = []
    m = request.node.get_closest_marker('inventory_assets')
    if m:
        for spec in list(m.args):
            spec['onyo.path.absolute'] = gitrepo.root / spec['onyo.path.relative']
            implicit_dirs = [d for d in spec['onyo.path.absolute'].parents
                             if gitrepo.root in d.parents]
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

    with pytest.MonkeyPatch.context() as m:
        m.chdir(gitrepo.root)

        yield onyo


@pytest.fixture(scope='function', name='onyorepo')
def onyorepo_function_scope(gitrepo,
                            request) -> Generator:
    r"""Scope the ``onyorepo`` parameter fixture for functions."""

    with fixture_onyorepo(gitrepo, request) as result:
        yield result


@pytest.fixture(scope='class')
def onyorepo_class_scope(gitrepo_class_scope,
                         request) -> Generator:
    r"""Scope the ``onyorepo`` parameter fixture for classes."""

    with fixture_onyorepo(gitrepo_class_scope, request) as result:
        yield result


@pytest.fixture(scope='module')
def onyorepo_module_scope(gitrepo_module_scope,
                          request) -> Generator:
    r"""Scope the ``onyorepo`` parameter fixture for modules."""

    with fixture_onyorepo(gitrepo_module_scope, request) as result:
        yield result


@pytest.fixture(scope='session')
def onyorepo_session_scope(gitrepo_session_scope,
                           request) -> Generator:
    r"""Scope the ``onyorepo`` parameter fixture for sessions."""

    with fixture_onyorepo(gitrepo_session_scope, request) as result:
        yield result


########################################
#
# repo
#
########################################
@contextmanager
def fixture_repo(tmp_path: Path,
                 request) -> Generator[OnyoRepo, None, None]:
    r"""Yield an OnyoRepo object, populated from fixtures.

    A fresh repository is created in a unique temporary directory. It is then
    populated via these markers:

    - ``repo_dirs()``
    - ``repo_files()`` (parent directories of files are automatically created)

    Example::

      repo_dirs("a/b/c", "1/2/3")
      repo_files("here/type_make_model.1", "there/type_make_model.2")
    """

    repo_path = tmp_path
    dirs = set()
    files = set()
    contents = list()

    # initialize repo
    repo_ = OnyoRepo(repo_path, init=True)
    repo_.set_config("onyo.assets.name-format", "{type}_{make}_{model.name}.{serial}")
    repo_.git.commit(repo_.onyo_config, message="Asset name config w/ dot")
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

    with pytest.MonkeyPatch.context() as m:
        m.chdir(repo_path)

        yield repo_


@pytest.fixture(scope='function', name='repo')
def repo_function_scope(tmp_path: Path,
                        request) -> Generator:
    r"""Scope the ``repo`` parameter fixture for functions."""

    with fixture_repo(tmp_path, request) as result:
        yield result


@pytest.fixture(scope='class')
def repo_class_scope(tmp_path_class_scope: Path,
                     request) -> Generator:
    r"""Scope the ``repo`` parameter fixture for classes."""

    with fixture_repo(tmp_path_class_scope, request) as result:
        yield result


@pytest.fixture(scope='module')
def repo_module_scope(tmp_path_module_scope: Path,
                      request) -> Generator:
    r"""Scope the ``repo`` parameter fixture for modules."""

    with fixture_repo(tmp_path_module_scope, request) as result:
        yield result


@pytest.fixture(scope='session')
def repo_session_scope(tmp_path_session_scope: Path,
                       request) -> Generator:
    r"""Scope the ``repo`` parameter fixture for sessions."""

    with fixture_repo(tmp_path_session_scope, request) as result:
        yield result


########################################
#
# inventory
#
########################################
@contextmanager
def fixture_inventory(repo: OnyoRepo) -> Generator[Inventory, None, None]:
    r"""Yield a populated Inventory object.

    The inventory is populated with the following directories:

    - different/place/
    - empty/
    - somewhere/nested/

    And the following asset:

    - somewhere/nested/TYPE_MAKER_MODEL.SERIAL
    """

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
    inventory.add_directory(Item(repo.git.root / 'empty', repo=inventory.repo))
    inventory.add_directory(Item(repo.git.root / 'different' / 'place', repo=inventory.repo))
    inventory.commit("First asset added")

    yield inventory


@pytest.fixture(scope='function', name='inventory')
def inventory_function_scope(repo: OnyoRepo) -> Generator:
    r"""Scope the ``inventory`` parameter fixture for functions."""

    with fixture_inventory(repo) as result:
        yield result


@pytest.fixture(scope='class')
def inventory_class_scope(repo_class_scope: OnyoRepo) -> Generator:
    r"""Scope the ``inventory`` parameter fixture for classes."""

    with fixture_inventory(repo_class_scope) as result:
        yield result


@pytest.fixture(scope='module')
def inventory_module_scope(repo_module_scope: OnyoRepo) -> Generator:
    r"""Scope the ``inventory`` parameter fixture for modules."""

    with fixture_inventory(repo_module_scope) as result:
        yield result


@pytest.fixture(scope='session')
def inventory_session_scope(repo_session_scope: OnyoRepo) -> Generator:
    r"""Scope the ``inventory`` parameter fixture for sessions."""

    with fixture_inventory(repo_session_scope) as result:
        yield result


########################################
#
# helpers
#
########################################
class Helpers:
    r"""A collection of helper utilities for tests."""

    @staticmethod
    def flatten(xs: Iterable) -> Generator:
        r"""Yield a flattened Iterable.

        Flatten a multidimensional list into a single dimension.
        """

        for x in xs:
            if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
                yield from Helpers.flatten(x)
            else:
                yield x

    @staticmethod
    def onyo_flags() -> List[List[List[str]] | List[str]]:
        r"""Return a List of all top level flags."""

        return [['-d', '--debug'],
                [['-C', '/tmp'], ['--onyopath', '/tmp']],
                ]

    @staticmethod
    def powerset(iterable: Iterable) -> chain[Tuple]:
        r"""Yield the powerset.

        Each subset is returned as its own Tuple. For example::

          powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
        """

        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


@contextmanager
def fixture_helpers() -> Generator[Type[Helpers], None, None]:
    r"""Return a Helper object with various helper utilities.

    See Also
    --------
    Helpers
    """

    yield Helpers


@pytest.fixture(scope='function', name='helpers')
def helpers_function_scope() -> Generator:
    r"""Scope the ``helpers`` parameter fixture for functions."""

    with fixture_helpers() as result:
        yield result


@pytest.fixture(scope='class')
def helpers_class_scope() -> Generator:
    r"""Scope the ``helpers`` parameter fixture for classes."""

    with fixture_helpers() as result:
        yield result


@pytest.fixture(scope='module')
def helpers_module_scope() -> Generator:
    r"""Scope the ``helpers`` parameter fixture for modules."""

    with fixture_helpers() as result:
        yield result


@pytest.fixture(scope='session')
def helpers_session_scope() -> Generator:
    r"""Scope the ``helpers`` parameter fixture for sessions."""

    with fixture_helpers() as result:
        yield result


########################################
#
# ui
#
########################################
@contextmanager
def fixture_ui(request) -> Generator:
    r"""Configure :py:class:`onyo.lib.ui.UI`.

    Applies values from a dict defined by the ``ui`` marker.

    Supported keys are: ``'yes'``, ``'quiet'``, and ``'debug'``. All accept
    booleans.

    See Also
    --------
    onyo.lib.ui.UI
    """

    from onyo.lib.ui import ui

    m = request.node.get_closest_marker('ui')
    if m:
        ui.set_yes(m.args[0].get('yes', False))
        ui.set_quiet(m.args[0].get('quiet', False))
        ui.set_debug(m.args[0].get('debug', False))

    yield


@pytest.fixture(scope='function', autouse=True)
def ui_function_scope(request) -> Generator:
    r"""Scope the ``ui`` marker for functions."""

    with fixture_ui(request) as result:
        yield result


@pytest.fixture(scope='class', autouse=True)
def ui_class_scope(request) -> Generator:
    r"""Scope the ``ui`` marker for classes."""

    with fixture_ui(request) as result:
        yield result


@pytest.fixture(scope='module', autouse=True)
def ui_module_scope(request) -> Generator:
    r"""Scope the ``ui`` marker for modules."""

    with fixture_ui(request) as result:
        yield result


@pytest.fixture(scope='session', autouse=True)
def ui_session_scope(request) -> Generator:
    r"""Scope the ``ui`` marker for sessions."""

    with fixture_ui(request) as result:
        yield result


########################################
#
# fake
#
########################################
@contextmanager
def fixture_fake() -> Generator:
    r"""Yield a Faker object with the Onyo provider loaded.

    See Also
    --------
    onyo.lib.faker.OnyoProvider
    """

    from faker import Faker

    _fake = Faker()
    _fake.add_provider(OnyoProvider)
    yield _fake


@pytest.fixture(scope='function', name='fake')
def fake_function_scope() -> Generator:
    r"""Scope the ``fake`` parameter fixture for functions."""

    with fixture_fake() as result:
        yield result


@pytest.fixture(scope='class')
def fake_class_scope() -> Generator:
    r"""Scope the ``fake`` parameter fixture for classes."""

    with fixture_fake() as result:
        yield result


@pytest.fixture(scope='module')
def fake_module_scope() -> Generator:
    r"""Scope the ``fake`` parameter fixture for modules."""

    with fixture_fake() as result:
        yield result


@pytest.fixture(scope='session')
def fake_session_scope() -> Generator:
    r"""Scope the ``fake`` parameter fixture for sessions."""

    with fixture_fake() as result:
        yield result
