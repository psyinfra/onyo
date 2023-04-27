import os
import subprocess
from typing import Union
from pathlib import Path

import pytest
from onyo import Repo, OnyoInvalidRepoError
from tests.conftest import params


#
# instantiation
#
@params({
    "Path": {"variant": Path("the-repo")},
    "str": {"variant": "the-repo"},
})
def test_Repo_instantiate_types(
        tmp_path: Path, variant: Union[str, Path]) -> None:
    """
    The Repo class must instantiate correctly for different data types for
    paths to existing repositories.
    """
    os.chdir(tmp_path)
    ret = subprocess.run(['onyo', 'init', 'the-repo'])
    assert ret.returncode == 0

    # test
    Repo(variant)


def test_Repo_instantiate_invalid_path(tmp_path: Path) -> None:
    """
    The Repo class must raise a `OnyoInvalidRepoError` if instantiated with a
    non-existing path.
    """
    repo_path = Path(tmp_path, 'does-not-exist')

    with pytest.raises(OnyoInvalidRepoError):
        Repo(repo_path)


def test_Repo_instantiate_empty_dir(tmp_path: Path) -> None:
    """
    The Repo class must raise a `OnyoInvalidRepoError` if instantiated with a
    path that is not an Onyo repository.
    """
    with pytest.raises(OnyoInvalidRepoError):
        Repo(tmp_path)


def test_Repo_instantiate_git_no_onyo(tmp_path: Path) -> None:
    """
    The Repo class must raise a `OnyoInvalidRepoError` if instantiated on a
    git repository that is not an Onyo repository.
    """
    ret = subprocess.run(['git', 'init', str(tmp_path)])
    assert ret.returncode == 0

    # test
    with pytest.raises(OnyoInvalidRepoError):
        Repo(tmp_path)


def test_Repo_instantiate_onyo_no_git(tmp_path: Path) -> None:
    """
    The Repo class must raise a `OnyoInvalidRepoError` if instantiated with a
    path that contains a `.onyo/` that is not a git repository.
    """
    Path(tmp_path, '.onyo').mkdir()

    with pytest.raises(OnyoInvalidRepoError):
        Repo(tmp_path)


#
# Initialization
#
def fully_populated_dot_onyo(directory: Union[Path, str]) -> bool:
    """
    Assert whether a .onyo dir is fully populated.
    """
    dot_onyo = Path(directory, '.onyo')

    if not Path(dot_onyo).is_dir() or \
       not Path(dot_onyo, "templates").is_dir() or \
       not Path(dot_onyo, "validation").is_dir() or \
       not Path(dot_onyo, "config").is_file() or \
       not Path(dot_onyo, ".anchor").is_file() or \
       not Path(dot_onyo, "templates/.anchor").is_file() or \
       not Path(dot_onyo, "validation/.anchor").is_file():
           return False  # noqa: E111, E117
    # TODO: assert that no unstaged or untracked under .onyo/

    return True


@params({
    "Path": {"variant": Path("dir")},
    "str": {"variant": "dir"},
})
def test_init_types(tmp_path: Path, variant: Union[str, Path]) -> None:
    """
    Test that `Repo(<directory>, init=True)` initializes an Onyo Repository for
    an existing, empty directory.
    """
    os.chdir(tmp_path)

    # test
    Repo(variant, init=True)
    assert fully_populated_dot_onyo(variant)


def test_init_False(tmp_path: Path) -> None:
    """
    `Repo(<directory>, init=False)` must not create onyo-files when it is
    initialized a path that is not already an Onyo Repository.
    """
    with pytest.raises(OnyoInvalidRepoError):
        Repo(tmp_path, init=False)
    assert not fully_populated_dot_onyo(tmp_path)


@pytest.mark.parametrize('variant', ['dir', 's p a c e s'])
def test_init_not_exist_dir(tmp_path: Path, variant: str) -> None:
    """
    Init a non-existent directory.
    """
    repo_path = Path(tmp_path, variant).resolve()

    # test
    Repo(repo_path, init=True)
    assert fully_populated_dot_onyo(repo_path)


def test_init_and_find_root_true(tmp_path: Path) -> None:
    """
    `Repo(<directory>, init=True, find_root=True)` is ambiguous and disallowed.
    """
    with pytest.raises(ValueError):
        Repo(tmp_path, init=True, find_root=True)


@pytest.mark.parametrize('variant', ['', './', 'dir', 's p a c e s'])
def test_init_exist_dir(tmp_path: Path, variant: str) -> None:
    """
    Test init for an existing, empty directory.
    """
    os.chdir(tmp_path)
    repo_path = Path(tmp_path, variant)
    repo_path.mkdir(exist_ok=True, parents=True)

    # test
    Repo(repo_path, init=True)
    assert fully_populated_dot_onyo(repo_path)


@pytest.mark.parametrize('variant', ['./', 'dir', 's p a c e s'])
def test_init_reinit(tmp_path: Path, variant: str) -> None:
    """
    `Repo(<directory>, init=True)` must raise a `FileExistsError` on a path that
    is already an Onyo repository.
    """
    os.chdir(tmp_path)
    repo_path = Path(tmp_path, variant)
    Repo(repo_path, init=True)

    # test
    with pytest.raises(FileExistsError):
        Repo(repo_path, init=True)

    # nothing should be lost
    assert fully_populated_dot_onyo(repo_path)
    # nothing should be created
    assert not Path(repo_path, '.onyo/', '.onyo/').exists()


def test_init_file(tmp_path: Path) -> None:
    """
    Instantiation of Repo() on a file must raise a `FileExistsError`.
    """
    repo_path = Path(tmp_path, 'file').resolve()
    repo_path.touch()

    # test
    with pytest.raises(FileExistsError):
        Repo(repo_path, init=True)


def test_init_missing_parent_dir(tmp_path: Path) -> None:
    """
    Parent directories must exist.
    """
    repo_path = Path(tmp_path, 'missing', 'parent', 'dir').resolve()

    # test
    with pytest.raises(FileNotFoundError):
        Repo(repo_path, init=True)

    assert not fully_populated_dot_onyo(repo_path)
    for i in repo_path.parents:
        assert not fully_populated_dot_onyo(i)


def test_init_already_git(tmp_path: Path) -> None:
    """
    Init-ing a git repo is allowed.
    """
    repo_path = tmp_path.resolve()
    ret = subprocess.run(['git', 'init', repo_path])
    assert ret.returncode == 0

    # test
    Repo(repo_path, init=True)
    assert fully_populated_dot_onyo(repo_path)


def test_init_with_cruft(tmp_path: Path) -> None:
    """
    Init-ing a directory with content is allowed, and should not commit anything
    other than the newly created .onyo dir.
    """
    repo_path = tmp_path.resolve()
    Path(repo_path, 'dir').mkdir()
    Path(repo_path, 'dir', 'such_cruft.txt').touch()

    # test
    repo = Repo(repo_path, init=True)
    assert fully_populated_dot_onyo(repo_path)
    assert Path('dir', 'such_cruft.txt') not in repo.files


#
# Repo.assets
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6',
                        'd/7', 'd/8')
def test_Repo_assets(repo: Repo) -> None:
    """
    On instantiation the property Repo.assets must contain the assets of an
    existing repository.
    """
    assets = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # test
    assert repo.assets
    assert isinstance(repo.assets, set)

    # fewer assets than files
    assert len(repo.assets) < len(repo.files)

    for i in repo.assets:
        assert isinstance(i, Path)
        assert i.is_file()
        assert i.is_absolute()
        # nothing from .git
        assert '.git' not in i.parts
        # nothing from .onyo
        assert '.onyo' not in i.parts
        # no anchors
        assert '.anchor' != i.name
        # TODO: make sure name pattern is for an asset (e.g. not README)

    # make sure all created files are returned
    for i in assets:
        # TODO: only check assets
        assert [x for x in repo.files if x.samefile(Path(i))]


#
# Repo.dirs
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6',
                        'd/7', 'd/8')
def test_Repo_dirs(repo: Repo) -> None:
    """
    On instantiation the property Repo.dirs must contain the directories of an
    existing repository.
    """
    dirs = ['a', 'b', 'c', 'd']

    # test
    assert repo.dirs
    assert isinstance(repo.dirs, set)

    for i in repo.dirs:
        assert isinstance(i, Path)
        assert i.is_dir()
        assert i.is_absolute()
        # nothing from .git
        assert '.git' not in i.parts

    # make sure all created dirs are returned
    for i in dirs:
        assert [x for x in repo.dirs if x.samefile(Path(i))]

    # should include .onyo
    assert [x for x in repo.dirs if '.onyo' in x.parts]


#
# Repo.files
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6',
                        'd/7', 'd/8')
def test_Repo_files(repo: Repo) -> None:
    """
    On instantiation the property Repo.files must contain the files of an
    existing repository.
    """
    files = ['README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6', 'd/7', 'd/8']

    # test
    assert repo.files
    assert isinstance(repo.files, set)

    for i in repo.files:
        assert isinstance(i, Path)
        assert i.is_file()
        assert i.is_absolute()
        # nothing from .git
        assert '.git' not in i.parts

    # make sure all created files are returned
    for i in files:
        assert [x for x in repo.files if x.samefile(Path(i))]

    # should include .onyo
    assert [x for x in repo.files if '.onyo' in x.parts]
    # should include .anchors
    assert [x for x in repo.files if '.anchor' == x.name]


#
# Repo.files_changed
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6',
                        'd/7', 'd/8')
def test_Repo_files_changed(repo: Repo) -> None:
    """
    On instantiation the property Repo.files_changed must contain the changed
    files of an existing repository.
    """
    files_to_change = ['a/1', 'b/3']
    # change files
    for i in files_to_change:
        Path(i).write_text('New contents')

    # test
    assert repo.files_changed
    assert isinstance(repo.files_changed, set)
    assert len(files_to_change) == len(repo.files_changed)

    for i in repo.files_changed:
        assert isinstance(i, Path)
        assert i.is_file()
        assert i.is_absolute()

    # make sure all changed files are returned
    for i in files_to_change:
        assert [x for x in repo.files_changed if x.samefile(Path(i))]


#
# Repo.files_staged
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6',
                        'd/7', 'd/8')
def test_Repo_files_staged(repo: Repo) -> None:
    """
    On instantiation the property Repo.files_staged must contain the
    staged files of an existing repository.
    """
    files_to_stage = ['a/1', 'b/3']

    # change and stage files
    for i in files_to_stage:
        Path(i).write_text('New contents')

    repo.add(files_to_stage)

    # test
    assert repo.files_staged
    assert isinstance(repo.files_staged, set)
    assert len(files_to_stage) == len(repo.files_staged)

    for i in repo.files_staged:
        assert isinstance(i, Path)
        assert i.is_file()
        assert i.is_absolute()

    # make sure all staged files are returned
    for i in files_to_stage:
        assert [x for x in repo.files_staged if x.samefile(Path(i))]


#
# Repo.files_untracked
#
@pytest.mark.repo_files('README', 'a/1', 'a/2', 'b/3', 'b/4', 'c/5', 'c/6',
                        'd/7', 'd/8')
def test_Repo_files_untracked(repo: Repo) -> None:
    """
    On instantiation the property Repo.files_untracked must contain the
    untracked files of an existing repository.
    """

    files_to_be_untracked = ['LICENSE', 'd/9']

    # create untracked files
    for i in files_to_be_untracked:
        Path(i).touch()

    # test
    assert repo.files_untracked
    assert isinstance(repo.files_untracked, set)
    assert len(files_to_be_untracked) == len(repo.files_untracked)

    for i in repo.files_untracked:
        assert isinstance(i, Path)
        assert i.is_file()
        assert i.is_absolute()

    # make sure all untracked files are returned
    for i in files_to_be_untracked:
        assert [x for x in repo.files_untracked if x.samefile(Path(i))]


#
# Repo.opdir
#
def test_Repo_opdir(tmp_path: Path) -> None:
    """
    On instantiation the property Repo.opdir must contain the
    operating directory of an existing repository.
    """
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-repo'])
    assert ret.returncode == 0

    # test
    repo = Repo('opdir-repo')
    assert isinstance(repo.opdir, Path)
    assert repo.opdir.is_absolute()
    assert Path('opdir-repo').samefile(repo.opdir)


def test_Repo_opdir_root(tmp_path: Path) -> None:
    """
    When instantiated with '.' as the path, the property Repo.opdir must contain
    the operating directory as a Path.
    """
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'opdir-root'])
    assert ret.returncode == 0

    # test
    os.chdir('opdir-root')
    repo = Repo('.')
    assert Path('.').samefile(repo.opdir)
    assert repo.opdir.is_absolute()
    assert repo.root.samefile(repo.opdir)


@pytest.mark.repo_dirs('1/2/3/4/5/6')
def test_Repo_opdir_child(repo: Repo, tmp_path: Path) -> None:
    """
    An existing Repo must be instantiated with the root of a repository,
    otherwise an error is raised.
    """
    os.chdir(repo.root / '1' / '2' / '3' / '4' / '5' / '6')

    # test error response
    with pytest.raises(OnyoInvalidRepoError):
        repo = Repo('.')

    repo = Repo('.', find_root=True)
    assert tmp_path.samefile(repo.root)
    assert repo.opdir.is_absolute()


#
# Repo.root
#
def test_Repo_root(tmp_path: Path) -> None:
    """
    The property `repo.root` must be set correctly.
    """
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-repo'])
    assert ret.returncode == 0

    repo = Repo('root-repo')
    assert repo.root.is_absolute()
    assert isinstance(repo.root, Path)


def test_Repo_root_parent(tmp_path: Path) -> None:
    """
    The property `repo.root` must be set correctly.
    """
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-parent'])
    assert ret.returncode == 0

    # test
    repo = Repo('root-parent')
    assert repo.root.is_absolute()
    assert Path('root-parent').samefile(repo.root)


def test_Repo_root_root(tmp_path: Path) -> None:
    """
    The property `repo.root` must be set correctly when Repo(".") is
    instantiated with a "." as path.
    """
    os.chdir(tmp_path)

    # setup repo
    ret = subprocess.run(['onyo', 'init', 'root-root'])
    assert ret.returncode == 0

    # test
    os.chdir('root-root')
    repo = Repo('.')
    assert repo.root.is_absolute()
    assert Path('.').samefile(repo.root)

#
# Repo._find_root()
#

@pytest.mark.repo_dirs('1/2/3/4/5/6')
def test_Repo_find_root_opdir_root(repo: Repo) -> None:
    """
    When the cwd is in the repo root, `Repo._find_root()` just returns the root.
    a `Repo` can be instantiated with `Repo(<opdir>, find_root=True)`.
    """
    os.chdir(repo.root)
    new_repo = Repo(repo.root, find_root=True)
    assert new_repo.root.samefile(repo.root)


@pytest.mark.repo_dirs('1/2/3/4/5/6')
def test_Repo_find_root_opdir_child(repo: Repo) -> None:
    """
    When the cwd is inside an existing repo, a `Repo` can be instantiated with
    `Repo(<opdir>, find_root=True)`.
    """
    path_deep_within = repo.root / '1' / '2' / '3' / '4' / '5' / '6'
    os.chdir(path_deep_within)
    new_repo = Repo(path_deep_within, find_root=True)
    assert new_repo.root.samefile(repo.root)


def test_Repo_find_root_with_no_repository_path(tmp_path: Path) -> None:
    """
    If `Repo._find_root()` is called on an existing path that is not a
    repository, it has to raise a `OnyoInvalidRepoError`
    """
    with pytest.raises(OnyoInvalidRepoError):
        Repo._find_root(tmp_path)


def test_Repo_find_root_with_non_existing_path(tmp_path: Path) -> None:
    """
    If `Repo._find_root()` is called on a path that does not exist, it has to
    raise a `OnyoInvalidRepoError`
    """
    with pytest.raises(OnyoInvalidRepoError):
        Repo._find_root(Path(tmp_path, "does_not_exist"))


#
# Repo.templates
#
def test_Repo_templates(repo: Repo) -> None:
    """
    The property repo.templates must be a set of Paths to templates with the
    right location without containing unwanted files.
    """
    # test
    assert repo.templates
    assert isinstance(repo.templates, set)

    # fewer templates than files
    assert len(repo.templates) < len(repo.files)

    for i in repo.templates:
        assert isinstance(i, Path)
        assert i.is_file()
        assert i.is_absolute()
        assert '.onyo' in i.parts and 'templates' in i.parts
        # nothing from .git
        assert '.git' not in i.parts
        # no anchors
        assert '.anchor' != i.name


def test_Repo_get_template(repo: Repo) -> None:
    """
    The function `repo.get_template()` must be able to return a Path for all
    templates in `repo.templates` when called with a string or a Path.
    """
    for i in repo.templates:
        template = repo.get_template(i)
        assert isinstance(template, Path)
        template = repo.get_template(str(i))
        assert isinstance(template, Path)
        template = repo.get_template(i.name)
        assert isinstance(template, Path)

        assert template.is_file()
        assert template.is_absolute()
        assert '.onyo' in template.parts and 'templates' in template.parts
        # nothing from .git
        assert '.git' not in template.parts
        # no anchors
        assert '.anchor' != template.name


def test_Repo_get_template_default(repo: Repo) -> None:
    """
    The function `repo.get_template()` must get the default template when
    called without argument.
    """
    template = repo.get_template()
    assert isinstance(template, Path)

    assert template.is_file()
    assert template.is_absolute()
    assert '.onyo' in template.parts and 'templates' in template.parts
    # nothing from .git
    assert '.git' not in template.parts
    # no anchors
    assert '.anchor' != template.name
