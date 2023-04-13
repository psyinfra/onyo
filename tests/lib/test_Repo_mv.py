import logging
from pathlib import Path
from typing import List

import pytest
from _pytest.logging import LogCaptureFixture
from onyo import OnyoProtectedPathError
from onyo.lib import Repo
from tests.conftest import params


#
# GENERIC
#
@pytest.mark.repo_dirs('src-dir')
@pytest.mark.repo_files('src-file')
@pytest.mark.parametrize('variant', [
    'src-dir',
    'src-file'
])
def test_missing_parent(caplog: LogCaptureFixture, repo: Repo,
                        variant: str) -> None:
    """
    Parent must exist. It is not possible to determine whether this is a rename
    or a move.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    with pytest.raises(FileNotFoundError):
        repo.mv(variant, 'does/not/exist/src.rename')

    assert Path(variant).exists()
    assert not Path('does').exists()
    assert 'does not exist' in caplog.text

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text
    assert 'rename mode' not in caplog.text


#
# RENAME
#
@pytest.mark.repo_dirs('dir')
@params({
    'src-str-dest-str': {'variant': ('dir', 'dir.rename')},
    'src-Path-dest-str': {'variant': (Path('dir'), 'dir.rename')},
    'src-str-dest-Path': {'variant': ('dir', Path('dir.rename'))},
    'src-Path-dest-Path': {'variant': (Path('dir'), Path('dir.rename'))},
    'src-list-str-dest-str': {'variant': (['dir'], 'dir.rename')},
    'src-list-Path-dest-str': {'variant': ([Path('dir')], 'dir.rename')},
    'src-list-str-dest-Path': {'variant': (['dir'], Path('dir.rename'))},
    'src-list-Path-dest-Path': {'variant': ([Path('dir')], Path('dir.rename'))},
    'src-set-str-dest-str': {'variant': ({'dir'}, 'dir.rename')},
    'src-set-Path-dest-str': {'variant': ({Path('dir')}, 'dir.rename')},
    'src-set-str-dest-Path': {'variant': ({'dir'}, Path('dir.rename'))},
    'src-set-Path-dest-Path': {'variant': ({Path('dir')}, Path('dir.rename'))},
})
def test_rename_types_dir(caplog: LogCaptureFixture, repo: Repo,
                          variant: List) -> None:
    """
    Rename a directory across types.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    repo.mv(*variant)
    assert not Path('dir').exists()
    assert Path('dir.rename').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text


@pytest.mark.repo_dirs('src-dir', 'dest-dir')
@params({
    'dest-cwd': {'variant': ('does-not-exist', 'does-not-exist.rename')},
    'dest-subdir': {'variant': ('does-not-exist',
                                'dest-dir/does-not-exist.rename')},
    'src-subdir-dest-cwd': {'variant': ('src-dir/does-not-exist',
                                        'does-not-exist.rename')},
    'src-subdir-dest-subdir': {'variant': ('src-dir/does-not-exist',
                                           'dest-dir/does-not-exist.rename')},
})
def test_rename_src_not_exist(caplog: LogCaptureFixture, repo: Repo,
                              variant: List) -> None:
    """
    Source paths must exist.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    src = Path(variant[0])
    dest = Path(variant[1])

    # test
    with pytest.raises(FileNotFoundError):
        repo.mv(*variant)

    assert not src.exists()
    assert not dest.exists()
    assert dest.parent.exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text
    assert 'source paths do not exist' in caplog.text


@pytest.mark.repo_dirs('src', 'subdir/src-two', 's p a c e s')
@params({
    'simple': {'variant': ('src', 'src.rename')},
    'into-subdir': {'variant': ('src', 'subdir/src.rename')},
    'out-of-subdir': {'variant': ('subdir/src-two', 'src-two.rename')},
    'spaces-source': {'variant': ('s p a c e s', 'spaces')},
    'spaces-dest': {'variant': ('src', 's r c')},
    'spaces-subdir-dest': {'variant': ('src', 's p a c e s/s r c')},
})
def test_rename_dir(caplog: LogCaptureFixture, repo: Repo,
                    variant: List) -> None:
    """
    Renaming a directory is allowed.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    repo.mv(*variant)

    assert not Path(variant[0]).exists()
    assert Path(variant[1]).exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text


@pytest.mark.repo_files('src', 'existing-file', 'subdir/src-two', 's p a c e s')
@params({
    'simple': {'variant': ('src', 'src.rename')},
    'into-subdir': {'variant': ('src', 'subdir/src.rename')},
    'out-of-subdir': {'variant': ('subdir/src-two', 'src-two.rename')},
    'spaces-source': {'variant': ('s p a c e s', 'spaces')},
    'spaces-dest': {'variant': ('src', 's r c')},
})
def test_rename_file(caplog: LogCaptureFixture, repo: Repo,
                     variant: List) -> None:
    """
    Renaming a file is not allowed.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    with pytest.raises(ValueError):
        repo.mv(*variant)

    assert Path(variant[0]).is_file()
    assert not Path(variant[1]).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text
    assert 'Cannot rename asset' in caplog.text


@pytest.mark.repo_dirs('src-dir')
@pytest.mark.repo_files('src-file', 'existing-file-1', 'subdir/existing-file-2')
@params({
    'dir-file': {'variant': ('src-dir', 'existing-file-1')},
    'file-file': {'variant': ('src-file', 'existing-file-1')},
    'dir-subfile': {'variant': ('src-dir', 'subdir/existing-file-2')},
    'file-subfile': {'variant': ('src-file', 'subdir/existing-file-2')},
})
def test_rename_conflict_file(caplog: LogCaptureFixture, repo: Repo,
                              variant: List) -> None:
    """
    Renaming onto an existing file is not allowed.

    This only tests renaming to conflicting file destinations because to
    "rename" to an existing destination dir is actually the syntax for moving
    the source into the destination dir.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    src = Path(variant[0])
    dest = Path(variant[1])

    # test
    with pytest.raises(FileExistsError):
        repo.mv(*variant)

    assert src.exists()
    assert dest.is_file()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text
    assert 'cannot be a file' in caplog.text


@pytest.mark.repo_dirs('dir')
@params({
    'root': {'variant': ['./', 'root.rename']},
    'dir': {'variant': ['dir', 'dir/dir.rename']},
})
def test_rename_dir_into_self(caplog: LogCaptureFixture, repo: Repo,
                              variant: List) -> None:
    """
    Renaming a directory into itself is not allowed.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    src = Path(variant[0])
    dest = Path(variant[1])

    # test
    with pytest.raises(ValueError):
        repo.mv(*variant)

    assert src.is_dir()
    assert not dest.exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text
    assert 'into itself' in caplog.text


@pytest.mark.repo_files('src-file')
@pytest.mark.repo_dirs('src-dir')
@params({
    'src-dir-git': {'variant': ('.git', 'new-git')},
    'src-dir-onyo': {'variant': ('.onyo', 'new-onyo')},
    'src-dir-git-subdir': {'variant': ('.git/objects', 'new-objects')},
    'src-dir-onyo-subdir': {'variant': ('.onyo/templates', 'new-templates')},
    'src-file-git': {'variant': ('.git/config', 'new-git-config')},
    'src-file-onyo': {'variant': ('.onyo/config', 'new-onyo-config')},
    'src-anchor': {'variant': ('src-dir/.anchor', 'new-anchor')},
    'dest-dir-git-subdir': {'variant': ('src-dir', '.git/new-src')},
    'dest-dir-onyo-subdir': {'variant': ('src-dir', '.onyo/new-src')},
    'dest-file-git': {'variant': ('src-file', '.git/new-src')},
    'dest-file-onyo': {'variant': ('src-file', '.onyo/new-src')},
    'dest-anchor-file': {'variant': ('src-file', '.anchor')},
    'dest-anchor-dir': {'variant': ('src-dir', '.anchor')},
    'inside-git': {'variant': ('.git/config', '.git/new-config')},
    'inside-onyo': {'variant': ('.onyo/templates', '.onyo/new-templates')},
})
def test_rename_protected(caplog: LogCaptureFixture, repo: Repo,
                          variant: List) -> None:
    """
    Protected paths.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    with pytest.raises(OnyoProtectedPathError):
        repo.mv(*variant)

    assert Path(variant[0]).exists()
    assert not Path(variant[1]).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'move mode' not in caplog.text


#
# MOVE
#
@pytest.mark.repo_dirs('src-dir', 'dest-dir')
@params({
    'src-str-dest-str': {'variant': ('src-dir', 'dest-dir')},
    'src-Path-dest-str': {'variant': (Path('src-dir'), 'dest-dir')},
    'src-str-dest-Path': {'variant': ('src-dir', Path('dest-dir'))},
    'src-Path-dest-Path': {'variant': (Path('src-dir'), Path('dest-dir'))},
    'src-list-str-dest-str': {'variant': (['src-dir'], 'dest-dir')},
    'src-list-Path-dest-str': {'variant': ([Path('src-dir')], 'dest-dir')},
    'src-list-str-dest-Path': {'variant': (['src-dir'], Path('dest-dir'))},
    'src-list-Path-dest-Path': {'variant':
                                ([Path('src-dir')], Path('dest-dir'))},
    'src-set-str-dest-str': {'variant': ({'src-dir'}, 'dest-dir')},
    'src-set-Path-dest-str': {'variant': ({Path('src-dir')}, 'dest-dir')},
    'src-set-str-dest-Path': {'variant': ({'src-dir'}, Path('dest-dir'))},
    'src-set-Path-dest-Path': {'variant':
                               ({Path('src-dir')}, Path('dest-dir'))},
})
def test_move_types_dir(caplog: LogCaptureFixture, repo: Repo,
                        variant: List) -> None:
    """
    Move a directory across types.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    repo.mv(*variant)
    assert not Path('src-dir').exists()
    assert Path('dest-dir', 'src-dir').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_dirs('dest-dir')
@pytest.mark.repo_files('src-file', 'dest-dir')
@params({
    'src-str-dest-str': {'variant': ('src-file', 'dest-dir')},
    'src-Path-dest-str': {'variant': (Path('src-file'), 'dest-dir')},
    'src-str-dest-Path': {'variant': ('src-file', Path('dest-dir'))},
    'src-Path-dest-Path': {'variant': (Path('src-file'), Path('dest-dir'))},
    'src-list-str-dest-str': {'variant': (['src-file'], 'dest-dir')},
    'src-list-Path-dest-str': {'variant': ([Path('src-file')], 'dest-dir')},
    'src-list-str-dest-Path': {'variant': (['src-file'], Path('dest-dir'))},
    'src-list-Path-dest-Path': {'variant':
                                ([Path('src-file')], Path('dest-dir'))},
    'src-set-str-dest-str': {'variant': ({'src-file'}, 'dest-dir')},
    'src-set-Path-dest-str': {'variant': ({Path('src-file')}, 'dest-dir')},
    'src-set-str-dest-Path': {'variant': ({'src-file'}, Path('dest-dir'))},
    'src-set-Path-dest-Path': {'variant':
                               ({Path('src-file')}, Path('dest-dir'))},
})
def test_move_types_file(caplog: LogCaptureFixture, repo: Repo,
                         variant: List) -> None:
    """
    Move a file across types.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    repo.mv(*variant)
    assert not Path('src-file').exists()
    assert Path('dest-dir', 'src-file').exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_dirs('src-dir-1', 'dest-dir')
@pytest.mark.repo_files('src-file-2', 'subdir/src-file-3')
@params({
    'src-list-str-dest-str': {'variant': (['src-dir-1', 'src-file-2',
                                           'subdir/src-file-3'], 'dest-dir')},
    'src-list-Path-dest-str': {'variant':
                               ([Path('src-dir-1'), Path('src-file-2'),
                                Path('subdir/src-file-3')], 'dest-dir')},
    'src-list-str-dest-Path': {'variant':
                               (['src-dir-1', 'src-file-2',
                                 'subdir/src-file-3'], Path('dest-dir'))},
    'src-list-Path-dest-Path': {'variant':
                                ([Path('src-dir-1'), Path('src-file-2'),
                                  Path('subdir/src-file-3')],
                                 Path('dest-dir'))},
    'src-list-mixed-dest-str': {'variant':
                                ([Path('src-dir-1'), 'src-file-2',
                                  Path('subdir/src-file-3')], 'dest-dir')},
    'src-list-mixed-dest-Path': {'variant':
                                 (['src-dir-1', Path('src-file-2'),
                                   'subdir/src-file-3'], Path('dest-dir'))},
    'src-set-str-dest-str': {'variant':
                             ({'src-dir-1', 'src-file-2', 'subdir/src-file-3'},
                              'dest-dir')},
    'src-set-Path-dest-str': {'variant':
                              ({Path('src-dir-1'), Path('src-file-2'),
                                Path('subdir/src-file-3')}, 'dest-dir')},
    'src-set-str-dest-Path': {'variant':
                              ({'src-dir-1', 'src-file-2', 'subdir/src-file-3'},
                               Path('dest-dir'))},
    'src-set-Path-dest-Path': {'variant':
                               ({Path('src-dir-1'), Path('src-file-2'),
                                 Path('subdir/src-file-3')}, Path('dest-dir'))},
    'src-set-mixed-dest-str': {'variant':
                               ({Path('src-dir-1'), 'src-file-2',
                                 Path('subdir/src-file-3')}, 'dest-dir')},
    'src-set-mixed-dest-Path': {'variant':
                                ({'src-dir-1', Path('src-file-2'),
                                  'subdir/src-file-3'}, Path('dest-dir'))},
})
def test_move_types_mixed(caplog: LogCaptureFixture, repo: Repo, variant: List) -> None:
    """
    Move multiple files and directories across types.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')

    # test
    repo.mv(*variant)

    for i in variant[0]:
        src = Path(i)
        assert not src.exists()
        assert src.parent.exists()
        assert Path('dest-dir', src.name).exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_dirs('src-dir/src-subdir', 'dest-dir/dest-subdir', 'd e s t/d i r', 'name-1', 'same/name-1', 'same/name-2')
@pytest.mark.repo_files('src-file', 'srcdir/src-subfile', 's r c f i l e', 'name-2')
@params({
    'src-dir-dest-dir': {'variant': ('src-dir', 'dest-dir')},
    'src-subdir-dest-dir': {'variant': ('src-dir/src-subdir', 'dest-dir')},
    'src-file-dest-dir': {'variant': ('src-file', 'dest-dir')},
    'src-subfile-dest-dir': {'variant': ('srcdir/src-subfile', 'dest-dir')},
    'src-dir-dest-subdir': {'variant': ('src-dir', 'dest-dir/dest-subdir')},
    'src-subdir-dest-subdir': {'variant':
                               ('src-dir/src-subdir', 'dest-dir/dest-subdir')},
    'src-file-dest-subdir': {'variant':
                             ('src-file', 'dest-dir/dest-subdir')},
    'src-subfile-dest-subdir': {'variant':
                                ('srcdir/src-subfile', 'dest-dir/dest-subdir')},
    'src-file-spaces': {'variant': ('s r c f i l e', 'dest-dir')},
    'src-file-dest-spaces': {'variant': ('src-file', 'd e s t/d i r')},
    'src-spaces-dest-spaces': {'variant': ('s r c f i l e', 'd e s t/d i r')},
    'seems-explicit-but-isnt-dir': {'variant': ('name-1', 'same/name-1')},
    'seems-explicit-but-isnt-file': {'variant': ('name-2', 'same/name-2')},
})
def test_move_single_implicit(caplog: LogCaptureFixture, repo: Repo,
                              variant: List) -> None:
    """
    Move a single item with an implicit destination name.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    src = Path(variant[0])
    dest = Path(variant[1])

    # test
    repo.mv(*variant)

    assert not src.exists()
    assert src.parent.exists()
    assert Path(dest, src.name).exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_files('src-file', 'srcdir/src-subfile', 's r c f i l e')
@pytest.mark.repo_dirs('src-dir/src-subdir', 'dest-dir/dest-subdir',
                       'd e s t/d i r')
@params({
    'src-dir-dest-dir': {'variant': ('src-dir', 'dest-dir/src-dir')},
    'src-subdir-dest-dir': {'variant':
                            ('src-dir/src-subdir', 'dest-dir/src-subdir')},
    'src-file-dest-dir': {'variant': ('src-file', 'dest-dir/src-file')},
    'src-subfile-dest-dir': {'variant':
                             ('srcdir/src-subfile', 'dest-dir/src-subfile')},
    'src-dir-dest-subdir': {'variant':
                            ('src-dir', 'dest-dir/dest-subdir/src-dir')},
    'src-subdir-dest-subdir': {'variant':
                               ('src-dir/src-subdir',
                                'dest-dir/dest-subdir/src-subdir')},
    'src-file-dest-subdir': {'variant':
                             ('src-file', 'dest-dir/dest-subdir/src-file')},
    'src-subfile-dest-subdir': {'variant':
                                ('srcdir/src-subfile',
                                 'dest-dir/dest-subdir/src-subfile')},
    'src-file-spaces': {'variant': ('s r c f i l e', 'dest-dir/s r c f i l e')},
    'src-file-dest-spaces': {'variant': ('src-file', 'd e s t/d i r/src-file')},
    'src-spaces-dest-spaces': {'variant':
                               ('s r c f i l e',
                                'd e s t/d i r/s r c f i l e')},
})
def test_move_single_explicit(caplog: LogCaptureFixture, repo: Repo,
                              variant: List) -> None:
    """
    Move a single item with an explicit destination name that /matches/ the
    source name (making it still a move, and not a rename).
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    src = Path(variant[0])
    dest = Path(variant[1])

    # test
    repo.mv(*variant)

    assert not src.exists()
    assert src.parent.exists()
    assert dest.exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_files('file-1', 'file-2', 'file-3', 'srcdir/subfile-1',
                        'srcdir/subfile-2', 'srcdir/subfile-3', 'f i l e')
@pytest.mark.repo_dirs(
    'dir-1', 'dir-2', 'dir-3', 'srcdir/subdir-1', 'srcdir/subdir-2',
    'srcdir/subdir-3', 'dest-dir/dest-subdir', 'd e s t/d i r')
@params({
    'src-files': {'variant': (['file-1', 'file-2', 'file-3'], 'dest-dir')},
    'src-dirs': {'variant': (['dir-1', 'dir-2', 'dir-3'], 'dest-dir')},
    'src-subfiles': {'variant':
                     (['srcdir/subfile-1', 'srcdir/subfile-2',
                       'srcdir/subfile-3'], 'dest-dir')},
    'src-subdirs': {'variant':
                    (['srcdir/subdir-1', 'srcdir/subdir-2', 'srcdir/subdir-3'],
                     'dest-dir')},
    'src-files-dest-subdir': {'variant':
                              (['file-1', 'file-2', 'file-3'],
                               'dest-dir/dest-subdir')},
    'src-dirs-dest-subdir': {'variant':
                             (['dir-1', 'dir-2', 'dir-3'],
                              'dest-dir/dest-subdir')},
    'src-subfiles-dest-subdir': {'variant':
                                 (['srcdir/subfile-1', 'srcdir/subfile-2',
                                   'srcdir/subfile-3'],
                                  'dest-dir/dest-subdir')},
    'src-subdirs-dest-subdir': {'variant':
                                (['srcdir/subdir-1', 'srcdir/subdir-2',
                                  'srcdir/subdir-3'], 'dest-dir/dest-subdir')},
    'mixed-files-dir': {'variant': (['file-1', 'dir-2', 'file-3'], 'dest-dir')},
    'mixed-depth': {'variant':
                    (['srcdir/subdir-1', 'file-2', 'file-3'],
                     'dest-dir/dest-subdir')},
    'spaces': {'variant': (['file-1', 'srcdir', 'f i l e'], 'd e s t/d i r/')},
})
def test_move_multiple(caplog: LogCaptureFixture, repo: Repo,
                       variant: List) -> None:
    """
    Move multiple sources.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    dest = Path(variant[1])

    # test
    repo.mv(*variant)

    sources = [variant[0]] if isinstance(variant[0], str) else variant[0]
    for i in sources:
        src = Path(i)
        assert not src.exists()
        assert src.parent.exists()
        assert Path(dest, src.name).exists()

    # everything should be staged
    assert not repo.files_changed
    assert repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_files('src-file', 'one', 'three')
@pytest.mark.repo_dirs('src-dir', 'dest-dir')
@params({
    'src-dir-git': {'variant': ('.git', 'dest-dir')},
    'src-dir-onyo': {'variant': ('.onyo', 'dest-dir')},
    'src-dir-git-subdir': {'variant': ('.git/objects', 'dest-dir')},
    'src-dir-onyo-subdir': {'variant': ('.onyo/templates', 'dest-dir')},
    'src-file-git': {'variant': ('.git/config', 'dest-dir')},
    'src-file-onyo': {'variant': ('.onyo/config', 'dest-dir')},
    'src-anchor': {'variant': ('src-dir/.anchor', './')},
    'dest-dir-git': {'variant': ('src-dir', '.git')},
    'dest-dir-onyo': {'variant': ('src-dir', '.onyo')},
    'dest-dir-git-subdir': {'variant': ('src-dir', '.git/objects')},
    'dest-dir-onyo-subdir': {'variant': ('src-dir', '.onyo/templates')},
    'dest-file-git': {'variant': ('src-file', '.git')},
    'dest-file-onyo': {'variant': ('src-file', '.onyo')},
    'inside-git': {'variant': ('.git/config', '.git/objects')},
    'inside-onyo': {'variant': ('.onyo/templates', '.onyo/validation')},
})
def test_move_protected(caplog: LogCaptureFixture, repo: Repo,
                        variant: List) -> None:
    """
    Protected paths.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    src = Path(variant[0])
    dest = Path(variant[1])

    # single
    with pytest.raises(OnyoProtectedPathError):
        repo.mv(*variant)

    assert src.exists()
    assert not Path(dest, src.name).exists()

    # multiple
    with pytest.raises(OnyoProtectedPathError):
        repo.mv(['one', src, 'three'], dest)

    assert Path('one').exists()
    assert Path(src).exists()
    assert Path('three').exists()

    assert not Path(dest, src.name).exists()
    if not dest.samefile('.'):
        assert not Path(dest, 'one').exists()
        assert not Path(dest, 'three').exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text


@pytest.mark.repo_dirs('dir', 'dest-dir', 'exist-dir-3')
@pytest.mark.repo_files('exist-file-1')
@params({
    'dest-implicit': {'variant': ('does-not-exist', 'dest-dir')},
    'dest-explicit': {'variant': ('does-not-exist', 'dest-dir/does-not-exist')},
    'src-subdir-dest-implicit': {'variant': ('dir/does-not-exist', 'dest-dir')},
    'src-subdir-dest-explicit': {'variant':
                                 ('dir/does-not-exist',
                                  'dest-dir/does-not-exist')},
    'multiple': {'variant': (['does-not-exist-1',
                              'dir/does-not-exist-2'], 'dest-dir')},
    'mixed': {'variant': (['exist-file-1', 'does-not-exist-2',
                           'exist-dir-3'], 'dest-dir')},
})
def test_move_src_not_exist(caplog: LogCaptureFixture, repo: Repo,
                            variant: List) -> None:
    """
    Source paths must exist.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    dest = Path(variant[1])

    # test
    with pytest.raises(FileNotFoundError):
        repo.mv(*variant)

    sources = [variant[0]] if isinstance(variant[0], str) else variant[0]
    for i in sources:
        src = Path(i)
        if dest.exists():  # implicit mode
            assert not Path(dest, src.name).exists()

    assert Path('exist-file-1').exists()
    assert Path('exist-dir-3').exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text
    assert 'source paths do not exist' in caplog.text


@pytest.mark.repo_dirs('src-dir/subdir', 'dest-dir')
@pytest.mark.repo_files('file-1', 'src-dir/file-2')
@params({
    'cwd': {'variant': ({'file-1', 'src-dir/file-2', 'src-dir/subdir'},
                        'does-not-exist')},
    'subdir': {'variant': ({'file-1', 'src-dir/file-2', 'src-dir/subdir'},
                           'dest-dir/does-not-exist')},
})
def test_move_dest_not_exist(caplog: LogCaptureFixture, repo: Repo,
                             variant: List) -> None:
    """
    Destination must exist in move mode with multiple sources.

    The explicit form ('src-dir' -> 'does-not-exist/src-dir') is covered by the
    missing parent checks.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    dest = Path(variant[1])

    # test
    with pytest.raises(FileNotFoundError):
        repo.mv(*variant)

    sources = [variant[0]] if isinstance(variant[0], str) else variant[0]
    for i in sources:
        src = Path(i)
        assert src.exists()
        assert not Path(dest, src.name).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text
    assert 'does not exist' in caplog.text


@pytest.mark.repo_dirs('dir')
@pytest.mark.repo_files('file-1', 'file-3')
@params({
    'implicit': {'variant': ('dir', 'dir')},
    'multiple': {'variant': (['file-1', 'dir', 'file-3'], 'dir')},
    'explicit': {'variant': ('dir', 'dir/dir')},
})
def test_move_into_self(caplog: LogCaptureFixture, repo: Repo,
                        variant: List) -> None:
    """
    Cannot move a directory into itself.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    dest = Path(variant[1])

    # test
    with pytest.raises(ValueError):
        repo.mv(*variant)

    sources = [variant[0]] if isinstance(variant[0], str) else variant[0]
    for i in sources:
        src = Path(i)
        assert src.exists()
        assert not Path(dest, src.name).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text
    assert 'into itself' in caplog.text


@pytest.mark.repo_dirs('conflict-dir', 'dir/conflict-dir',
                       'dir/conflict-cross-type', 'dir-2')
@pytest.mark.repo_files('file-1', 'conflict-cross-type', 'conflict-file')
@params({
    'self-dir': {'variant': ('conflict-dir', './')},
    'self-file': {'variant': ('conflict-file', './')},
    'self-file-explicit': {'variant': ('conflict-file', 'conflict-file')},
    'cross-file-to-dir': {'variant': ('conflict-cross-type', 'dir')},
    'cross-dir-to-file': {'variant': ('dir/conflict-cross-type', './')},
    'cross-dir-to-file-explicit': {'variant':
                                   ('dir/conflict-cross-type',
                                    './conflict-cross-type')},
    'multiple': {'variant':
                 (['file-1', 'conflict-cross-type', 'dir-2'], 'dir')},
})
def test_move_name_conflict(caplog: LogCaptureFixture, repo: Repo,
                            variant: List) -> None:
    """
    Names of files/directories cannot conflict.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    dest = Path(variant[1])

    # test
    with pytest.raises(FileExistsError):
        repo.mv(*variant)

    sources = [variant[0]] if isinstance(variant[0], str) else variant[0]
    for i in sources:
        src = Path(i)
        assert src.exists()
        assert not Path(dest, src.name, src.name).exists()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text
    assert 'destinations exist and would conflict' or 'cannot be a file' in caplog.text


@pytest.mark.repo_dirs('dir-1')
@pytest.mark.repo_files('file-1', 'file-2', 'file-3', 'subdir/file-4')
@params({
    'file': {'variant': (['file-1', 'file-2', 'dir-1'], 'file-3')},
    'subfile': {'variant': (['file-1', 'file-2', 'dir-1'], 'subdir/file-4')},
})
def test_move_dest_must_be_dir(caplog: LogCaptureFixture, repo: Repo,
                               variant: List) -> None:
    """
    The destination must be a directory.
    """
    caplog.set_level(logging.DEBUG, logger='onyo')
    dest = Path(variant[1])

    # test
    with pytest.raises(FileExistsError):
        repo.mv(*variant)

    sources = [variant[0]] if isinstance(variant[0], str) else variant[0]
    for i in sources:
        src = Path(i)
        assert src.exists()
        assert not Path(dest, src.name, src.name).exists()

    assert dest.is_file()

    # nothing should be changed
    assert not repo.files_changed
    assert not repo.files_staged
    assert not repo.files_untracked

    # check log
    assert 'rename mode' not in caplog.text
    assert 'cannot be a file' in caplog.text
