import logging
from pathlib import Path
import pytest
from onyo import commands  # noqa: F401
from onyo.lib import OnyoProtectedPathError


#
# GENERIC
#
variants = [
    'src-dir',
    'src-file',
]
@pytest.mark.repo_dirs('src-dir')
@pytest.mark.repo_files('src-file')
@pytest.mark.parametrize('variant', variants)
def test_missing_parent(repo, variant, caplog):
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
variants = {  # pyre-ignore[9]
    'src-str-dest-str': ('dir', 'dir.rename'),
    'src-Path-dest-str': (Path('dir'), 'dir.rename'),
    'src-str-dest-Path': ('dir', Path('dir.rename')),
    'src-Path-dest-Path': (Path('dir'), Path('dir.rename')),
    'src-list-str-dest-str': (['dir'], 'dir.rename'),
    'src-list-Path-dest-str': ([Path('dir')], 'dir.rename'),
    'src-list-str-dest-Path': (['dir'], Path('dir.rename')),
    'src-list-Path-dest-Path': ([Path('dir')], Path('dir.rename')),
    'src-set-str-dest-str': ({'dir'}, 'dir.rename'),
    'src-set-Path-dest-str': ({Path('dir')}, 'dir.rename'),
    'src-set-str-dest-Path': ({'dir'}, Path('dir.rename')),
    'src-set-Path-dest-Path': ({Path('dir')}, Path('dir.rename')),
}
@pytest.mark.repo_dirs('dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_types_dir(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'dest-cwd': ('does-not-exist', 'does-not-exist.rename'),
    'dest-subdir': ('does-not-exist', 'dest-dir/does-not-exist.rename'),
    'src-subdir-dest-cwd': ('src-dir/does-not-exist', 'does-not-exist.rename'),
    'src-subdir-dest-subdir': ('src-dir/does-not-exist', 'dest-dir/does-not-exist.rename'),
}
@pytest.mark.repo_dirs('src-dir', 'dest-dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_src_not_exist(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'simple': ('src', 'src.rename'),
    'into-subdir': ('src', 'subdir/src.rename'),
    'out-of-subdir': ('subdir/src-two', 'src-two.rename'),
    'spaces-source': ('s p a c e s', 'spaces'),
    'spaces-dest': ('src', 's r c'),
    'spaces-subdir-dest': ('src', 's p a c e s/s r c'),
}
@pytest.mark.repo_dirs('src', 'subdir/src-two', 's p a c e s')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_dir(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'simple': ('src', 'src.rename'),
    'into-subdir': ('src', 'subdir/src.rename'),
    'out-of-subdir': ('subdir/src-two', 'src-two.rename'),
    'spaces-source': ('s p a c e s', 'spaces'),
    'spaces-dest': ('src', 's r c'),
}
@pytest.mark.repo_files('src', 'existing-file', 'subdir/src-two', 's p a c e s')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_file(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'dir-file': ('src-dir', 'existing-file-1'),
    'file-file': ('src-file', 'existing-file-1'),
    'dir-subfile': ('src-dir', 'subdir/existing-file-2'),
    'file-subfile': ('src-file', 'subdir/existing-file-2'),
}
@pytest.mark.repo_dirs('src-dir')
@pytest.mark.repo_files('src-file', 'existing-file-1', 'subdir/existing-file-2')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_conflict_file(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'root': ('./', 'root.rename'),
    'dir': ('dir', 'dir/dir.rename'),
}
@pytest.mark.repo_dirs('dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_dir_into_self(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-dir-git': ('.git', 'new-git'),
    'src-dir-onyo': ('.onyo', 'new-onyo'),
    'src-dir-git-subdir': ('.git/objects', 'new-objects'),
    'src-dir-onyo-subdir': ('.onyo/templates', 'new-templates'),
    'src-file-git': ('.git/config', 'new-git-config'),
    'src-file-onyo': ('.onyo/config', 'new-onyo-config'),
    'src-anchor': ('src-dir/.anchor', 'new-anchor'),
    'dest-dir-git-subdir': ('src-dir', '.git/new-src'),
    'dest-dir-onyo-subdir': ('src-dir', '.onyo/new-src'),
    'dest-file-git': ('src-file', '.git/new-src'),
    'dest-file-onyo': ('src-file', '.onyo/new-src'),
    'dest-anchor-file': ('src-file', '.anchor'),
    'dest-anchor-dir': ('src-dir', '.anchor'),
    'inside-git': ('.git/config', '.git/new-config'),
    'inside-onyo': ('.onyo/templates', '.onyo/new-templates'),
}
@pytest.mark.repo_files('src-file')
@pytest.mark.repo_dirs('src-dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_rename_protected(repo, variant, caplog):
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
variants = {  # pyre-ignore[9]
    'src-str-dest-str': ('src-dir', 'dest-dir'),
    'src-Path-dest-str': (Path('src-dir'), 'dest-dir'),
    'src-str-dest-Path': ('src-dir', Path('dest-dir')),
    'src-Path-dest-Path': (Path('src-dir'), Path('dest-dir')),
    'src-list-str-dest-str': (['src-dir'], 'dest-dir'),
    'src-list-Path-dest-str': ([Path('src-dir')], 'dest-dir'),
    'src-list-str-dest-Path': (['src-dir'], Path('dest-dir')),
    'src-list-Path-dest-Path': ([Path('src-dir')], Path('dest-dir')),
    'src-set-str-dest-str': ({'src-dir'}, 'dest-dir'),
    'src-set-Path-dest-str': ({Path('src-dir')}, 'dest-dir'),
    'src-set-str-dest-Path': ({'src-dir'}, Path('dest-dir')),
    'src-set-Path-dest-Path': ({Path('src-dir')}, Path('dest-dir')),
}
@pytest.mark.repo_dirs('src-dir', 'dest-dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_types_dir(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-str-dest-str': ('src-file', 'dest-dir'),
    'src-Path-dest-str': (Path('src-file'), 'dest-dir'),
    'src-str-dest-Path': ('src-file', Path('dest-dir')),
    'src-Path-dest-Path': (Path('src-file'), Path('dest-dir')),
    'src-list-str-dest-str': (['src-file'], 'dest-dir'),
    'src-list-Path-dest-str': ([Path('src-file')], 'dest-dir'),
    'src-list-str-dest-Path': (['src-file'], Path('dest-dir')),
    'src-list-Path-dest-Path': ([Path('src-file')], Path('dest-dir')),
    'src-set-str-dest-str': ({'src-file'}, 'dest-dir'),
    'src-set-Path-dest-str': ({Path('src-file')}, 'dest-dir'),
    'src-set-str-dest-Path': ({'src-file'}, Path('dest-dir')),
    'src-set-Path-dest-Path': ({Path('src-file')}, Path('dest-dir')),
}
@pytest.mark.repo_dirs('dest-dir')
@pytest.mark.repo_files('src-file', 'dest-dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_types_file(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-list-str-dest-str': (['src-dir-1', 'src-file-2', 'subdir/src-file-3'], 'dest-dir'),
    'src-list-Path-dest-str': ([Path('src-dir-1'), Path('src-file-2'), Path('subdir/src-file-3')], 'dest-dir'),
    'src-list-str-dest-Path': (['src-dir-1', 'src-file-2', 'subdir/src-file-3'], Path('dest-dir')),
    'src-list-Path-dest-Path': ([Path('src-dir-1'), Path('src-file-2'), Path('subdir/src-file-3')], Path('dest-dir')),
    'src-list-mixed-dest-str': ([Path('src-dir-1'), 'src-file-2', Path('subdir/src-file-3')], 'dest-dir'),
    'src-list-mixed-dest-Path': (['src-dir-1', Path('src-file-2'), 'subdir/src-file-3'], Path('dest-dir')),
    'src-set-str-dest-str': ({'src-dir-1', 'src-file-2', 'subdir/src-file-3'}, 'dest-dir'),
    'src-set-Path-dest-str': ({Path('src-dir-1'), Path('src-file-2'), Path('subdir/src-file-3')}, 'dest-dir'),
    'src-set-str-dest-Path': ({'src-dir-1', 'src-file-2', 'subdir/src-file-3'}, Path('dest-dir')),
    'src-set-Path-dest-Path': ({Path('src-dir-1'), Path('src-file-2'), Path('subdir/src-file-3')}, Path('dest-dir')),
    'src-set-mixed-dest-str': ({Path('src-dir-1'), 'src-file-2', Path('subdir/src-file-3')}, 'dest-dir'),
    'src-set-mixed-dest-Path': ({'src-dir-1', Path('src-file-2'), 'subdir/src-file-3'}, Path('dest-dir')),
}
@pytest.mark.repo_dirs('src-dir-1', 'dest-dir')
@pytest.mark.repo_files('src-file-2', 'subdir/src-file-3')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_types_mixed(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-dir-dest-dir': ('src-dir', 'dest-dir'),
    'src-subdir-dest-dir': ('src-dir/src-subdir', 'dest-dir'),
    'src-file-dest-dir': ('src-file', 'dest-dir'),
    'src-subfile-dest-dir': ('srcdir/src-subfile', 'dest-dir'),
    'src-dir-dest-subdir': ('src-dir', 'dest-dir/dest-subdir'),
    'src-subdir-dest-subdir': ('src-dir/src-subdir', 'dest-dir/dest-subdir'),
    'src-file-dest-subdir': ('src-file', 'dest-dir/dest-subdir'),
    'src-subfile-dest-subdir': ('srcdir/src-subfile', 'dest-dir/dest-subdir'),
    'src-file-spaces': ('s r c f i l e', 'dest-dir'),
    'src-file-dest-spaces': ('src-file', 'd e s t/d i r'),
    'src-spaces-dest-spaces': ('s r c f i l e', 'd e s t/d i r'),
    'seems-explicit-but-isnt-dir': ('name-1', 'same/name-1'),
    'seems-explicit-but-isnt-file': ('name-2', 'same/name-2'),
}
@pytest.mark.repo_dirs('src-dir/src-subdir', 'dest-dir/dest-subdir', 'd e s t/d i r', 'name-1', 'same/name-1', 'same/name-2')
@pytest.mark.repo_files('src-file', 'srcdir/src-subfile', 's r c f i l e', 'name-2')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_single_implicit(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-dir-dest-dir': ('src-dir', 'dest-dir/src-dir'),
    'src-subdir-dest-dir': ('src-dir/src-subdir', 'dest-dir/src-subdir'),
    'src-file-dest-dir': ('src-file', 'dest-dir/src-file'),
    'src-subfile-dest-dir': ('srcdir/src-subfile', 'dest-dir/src-subfile'),
    'src-dir-dest-subdir': ('src-dir', 'dest-dir/dest-subdir/src-dir'),
    'src-subdir-dest-subdir': ('src-dir/src-subdir', 'dest-dir/dest-subdir/src-subdir'),
    'src-file-dest-subdir': ('src-file', 'dest-dir/dest-subdir/src-file'),
    'src-subfile-dest-subdir': ('srcdir/src-subfile', 'dest-dir/dest-subdir/src-subfile'),
    'src-file-spaces': ('s r c f i l e', 'dest-dir/s r c f i l e'),
    'src-file-dest-spaces': ('src-file', 'd e s t/d i r/src-file'),
    'src-spaces-dest-spaces': ('s r c f i l e', 'd e s t/d i r/s r c f i l e'),
}
@pytest.mark.repo_files('src-file', 'srcdir/src-subfile', 's r c f i l e')
@pytest.mark.repo_dirs('src-dir/src-subdir', 'dest-dir/dest-subdir', 'd e s t/d i r')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_single_explicit(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-files': (['file-1', 'file-2', 'file-3'], 'dest-dir'),
    'src-dirs': (['dir-1', 'dir-2', 'dir-3'], 'dest-dir'),
    'src-subfiles': (['srcdir/subfile-1', 'srcdir/subfile-2', 'srcdir/subfile-3'], 'dest-dir'),
    'src-subdirs': (['srcdir/subdir-1', 'srcdir/subdir-2', 'srcdir/subdir-3'], 'dest-dir'),
    'src-files-dest-subdir': (['file-1', 'file-2', 'file-3'], 'dest-dir/dest-subdir'),
    'src-dirs-dest-subdir': (['dir-1', 'dir-2', 'dir-3'], 'dest-dir/dest-subdir'),
    'src-subfiles-dest-subdir': (['srcdir/subfile-1', 'srcdir/subfile-2', 'srcdir/subfile-3'], 'dest-dir/dest-subdir'),
    'src-subdirs-dest-subdir': (['srcdir/subdir-1', 'srcdir/subdir-2', 'srcdir/subdir-3'], 'dest-dir/dest-subdir'),
    'mixed-files-dir': (['file-1', 'dir-2', 'file-3'], 'dest-dir'),
    'mixed-depth': (['srcdir/subdir-1', 'file-2', 'file-3'], 'dest-dir/dest-subdir'),
    'spaces': (['file-1', 'srcdir', 'f i l e'], 'd e s t/d i r/'),
}
@pytest.mark.repo_files('file-1', 'file-2', 'file-3', 'srcdir/subfile-1', 'srcdir/subfile-2', 'srcdir/subfile-3', 'f i l e')
@pytest.mark.repo_dirs('dir-1', 'dir-2', 'dir-3', 'srcdir/subdir-1', 'srcdir/subdir-2', 'srcdir/subdir-3', 'dest-dir/dest-subdir', 'd e s t/d i r')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_multiple(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'src-dir-git': ('.git', 'dest-dir'),
    'src-dir-onyo': ('.onyo', 'dest-dir'),
    'src-dir-git-subdir': ('.git/objects', 'dest-dir'),
    'src-dir-onyo-subdir': ('.onyo/templates', 'dest-dir'),
    'src-file-git': ('.git/config', 'dest-dir'),
    'src-file-onyo': ('.onyo/config', 'dest-dir'),
    'src-anchor': ('src-dir/.anchor', './'),
    'dest-dir-git': ('src-dir', '.git'),
    'dest-dir-onyo': ('src-dir', '.onyo'),
    'dest-dir-git-subdir': ('src-dir', '.git/objects'),
    'dest-dir-onyo-subdir': ('src-dir', '.onyo/templates'),
    'dest-file-git': ('src-file', '.git'),
    'dest-file-onyo': ('src-file', '.onyo'),
    'inside-git': ('.git/config', '.git/objects'),
    'inside-onyo': ('.onyo/templates', '.onyo/validation'),
}
@pytest.mark.repo_files('src-file', 'one', 'three')
@pytest.mark.repo_dirs('src-dir', 'dest-dir')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_protected(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'dest-implicit': ('does-not-exist', 'dest-dir'),
    'dest-explicit': ('does-not-exist', 'dest-dir/does-not-exist'),
    'src-subdir-dest-implicit': ('dir/does-not-exist', 'dest-dir'),
    'src-subdir-dest-explicit': ('dir/does-not-exist', 'dest-dir/does-not-exist'),
    'multiple': (['does-not-exist-1', 'dir/does-not-exist-2'], 'dest-dir'),
    'mixed': (['exist-file-1', 'does-not-exist-2', 'exist-dir-3'], 'dest-dir'),
}
@pytest.mark.repo_dirs('dir', 'dest-dir', 'exist-dir-3')
@pytest.mark.repo_files('exist-file-1')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_src_not_exist(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'cwd': ({'file-1', 'src-dir/file-2', 'src-dir/subdir'}, 'does-not-exist'),
    'subdir': ({'file-1', 'src-dir/file-2', 'src-dir/subdir'}, 'dest-dir/does-not-exist'),
}
@pytest.mark.repo_dirs('src-dir/subdir', 'dest-dir')
@pytest.mark.repo_files('file-1', 'src-dir/file-2')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_dest_not_exist(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'implicit': ('dir', 'dir'),
    'multiple': (['file-1', 'dir', 'file-3'], 'dir'),
    'explicit': ('dir', 'dir/dir'),
}
@pytest.mark.repo_dirs('dir')
@pytest.mark.repo_files('file-1', 'file-3')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_into_self(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'self-dir': ('conflict-dir', './'),
    'self-file': ('conflict-file', './'),
    'self-file-explicit': ('conflict-file', 'conflict-file'),
    'cross-file-to-dir': ('conflict-cross-type', 'dir'),
    'cross-dir-to-file': ('dir/conflict-cross-type', './'),
    'cross-dir-to-file-explicit': ('dir/conflict-cross-type', './conflict-cross-type'),
    'multiple': (['file-1', 'conflict-cross-type', 'dir-2'], 'dir'),
}
@pytest.mark.repo_dirs('conflict-dir', 'dir/conflict-dir', 'dir/conflict-cross-type', 'dir-2')
@pytest.mark.repo_files('file-1', 'conflict-cross-type', 'conflict-file')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_name_conflict(repo, variant, caplog):
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


variants = {  # pyre-ignore[9]
    'file': (['file-1', 'file-2', 'dir-1'], 'file-3'),
    'subfile': (['file-1', 'file-2', 'dir-1'], 'subdir/file-4'),
}
@pytest.mark.repo_dirs('dir-1')
@pytest.mark.repo_files('file-1', 'file-2', 'file-3', 'subdir/file-4')
@pytest.mark.parametrize('variant', variants.values(), ids=variants.keys())
def test_move_dest_must_be_dir(repo, variant, caplog):
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
