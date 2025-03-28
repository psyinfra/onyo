from pathlib import Path

import pytest

from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    IGNORE_FILE_NAME,
    TEMPLATE_DIR,
)
from onyo.lib.onyo import OnyoRepo, OnyoInvalidRepoError
from onyo.lib.items import (
    Item,
    ItemSpec,
)


def test_instantiation_existing(onyorepo: OnyoRepo) -> None:
    """Instantiate OnyoRepo with an existing repository."""

    new_repo = OnyoRepo(onyorepo.git.root, init=False)
    assert new_repo.git.root.samefile(onyorepo.git.root)


def test_instantiation_non_existing(tmp_path: Path) -> None:
    """Instantiate OnyoRepo with a non-existing repository."""

    new_repo = OnyoRepo(tmp_path, init=True)
    assert new_repo.git.root.samefile(tmp_path)
    assert (new_repo.git.root / '.onyo').is_dir()
    assert (new_repo.git.root / '.git').is_dir()
    # assert dirs/files in .onyo/ exist and are cached correctly
    assert all(x in new_repo.git.files for x in [new_repo.dot_onyo / f for f in [
        new_repo.dot_onyo / ANCHOR_FILE_NAME,
        new_repo.onyo_config,
        new_repo.template_dir / ANCHOR_FILE_NAME,
        new_repo.dot_onyo / 'validation' / ANCHOR_FILE_NAME,
    ]])
    assert new_repo.git.is_clean_worktree()
    new_repo.validate_onyo_repo()
    # a newly initialized repository has just one commit; requesting older ones is not possible
    assert new_repo.git.get_hexsha()
    pytest.raises(ValueError,
                  new_repo.git.get_hexsha,
                  'HEAD~1')


def test_incorrect_input_arguments_raise_error(onyorepo: OnyoRepo,
                                                        tmp_path: Path) -> None:
    """OnyoRepo riases for invalid or conflicting arguments.

    - raise a OnyoInvalidRepoError when called on a path that is
      not yet a valid onyo repository.
    - raise a `ValueError` when called with conflicting arguments
      `init=True` and `find_root=True`
    - raise a `FileExistsError` when trying to initialize a new OnyoRepo for a
      path that is already an OnyoRepo.
    """

    # try OnyoRepo with a non-repo path
    with pytest.raises(OnyoInvalidRepoError):
        OnyoRepo(tmp_path / 'no-existy', init=False)
    # try OnyoRepo initialization with a path which is already a repo
    with pytest.raises(FileExistsError):
        OnyoRepo(onyorepo.git.root, init=True)
    # try with conflicting arguments `init=True` and `find_root=True`
    with pytest.raises(ValueError):
        OnyoRepo(tmp_path, init=True, find_root=True)


@pytest.mark.inventory_assets(Item(type="asset",
                                   make="for",
                                   model="test",
                                   serial=0,
                                   path=Path('a') / 'test' / 'asset_for_test.0'))
def test_clear_cache(onyorepo) -> None:
    """``OnyoRepo.clear_cache()`` empties the cache."""

    # Use arbitrary asset here:
    asset = onyorepo.test_annotation['assets'][0]['onyo.path.absolute']

    # make sure asset is in the cache:
    assert asset in onyorepo.asset_paths

    # only committed state is considered:
    Path.unlink(asset)
    assert asset in onyorepo.asset_paths

    # committing while circumventing `OnyoRepo.commit` would
    # make the cache out-of-sync:
    onyorepo.git.commit(asset, "asset deleted")
    assert asset in onyorepo.asset_paths

    # clear_cache() fixes the cache:
    onyorepo.clear_cache()
    assert asset not in onyorepo.asset_paths


def test_generate_commit_subject(onyorepo: OnyoRepo) -> None:
    """Commit subject has correct asset count and paths are relative."""

    modified = [onyorepo.git.root / 's p a c e s',
                onyorepo.git.root / 'a/new/folder']

    # generate a commit message:
    message = onyorepo.generate_commit_subject(
        format_string='TST [{length}]: {modified}',
        length=len(modified),
        modified=modified)

    # root should not be in output
    assert str(onyorepo.git.root) not in message

    # verify all necessary information is in the message:
    assert f'TST [{len(modified)}]: ' in message


@pytest.mark.gitrepo_contents((Path('a/test/asset_for_test.0'), ""))
def test_is_onyo_path(onyorepo) -> None:
    """``is_onyo_path()` detects paths under `.onyo/` and outside of it."""

    # True for the directory `.onyo/` itself
    assert onyorepo.is_onyo_path(onyorepo.dot_onyo)
    # True for the directory `templates` inside of `.onyo/`
    assert onyorepo.is_onyo_path(onyorepo.template_dir)
    # True for a file inside `.onyo/`
    assert onyorepo.is_onyo_path(onyorepo.template_dir / 'empty')

    # other files/directories beginning with .onyo should be recognized too
    assert onyorepo.is_onyo_path(onyorepo.git.root / '.onyoignore')

    # False for root of onyo repository
    assert not onyorepo.is_onyo_path(onyorepo.git.root)
    # False for directory `.git/`
    assert not onyorepo.is_onyo_path(onyorepo.git.root / '.git')
    # False for directory inside an onyo repository
    assert all(not onyorepo.is_onyo_path(d)
               for d in onyorepo.test_annotation['git'].test_annotation['directories'])
    # False for file inside an onyo repository
    assert all(not onyorepo.is_onyo_path(f)
               for f in onyorepo.test_annotation['git'].test_annotation['files'])


def test_get_template_simple(onyorepo: OnyoRepo) -> None:
    """``get_template`` gets a dictionary of a template file.

    If a relative path is specified, it looks in ``.onyo/templates/`` first and
    then CWD.

    With no config and no name given, returns an empty dict.
    """

    # Call the function without parameter to get the empty template:
    assert onyorepo.get_templates().__next__() == ItemSpec()

    # from the 'templates' dir, use the filename of each template to find the
    # corresponding template file as a path.
    for path in onyorepo.template_dir.iterdir():
        if path.name == ANCHOR_FILE_NAME:
            continue

        # specify path as absolute or relative to template dir:
        for given_path in [path, path.relative_to(onyorepo.template_dir)]:
            template = onyorepo.get_templates(given_path).__next__()
            assert isinstance(template, ItemSpec)
            assert template != ItemSpec()

    # verify the correct error response when called with a template name that
    # does not exist
    with pytest.raises(ValueError):
        onyorepo.get_templates(Path('I DO NOT EXIST')).__next__()

    # TODO: test config


def test_get_empty_template_directory(onyorepo: OnyoRepo) -> None:
    template_base_dir = Path("packaged_templates")
    # regular, empty dir represented as such or as a yaml file specifying this dir:
    for p in ["empty_template_dir", "empty_template_dir_file"]:
        specs = [s for s in onyorepo.get_templates(template_base_dir / p, recursive=False)]
        assert len(specs) == 1
        assert specs[0]["onyo.is.directory"] is True
        #assert spec[is asset
        assert specs[0]["onyo.path.name"] == p
        assert specs[0]["onyo.path.parent"] == Path(".")
        # no difference when recursive:
        specs = [s for s in onyorepo.get_templates(template_base_dir / p, recursive=True)]
        assert len(specs) == 1
        assert specs[0]["onyo.is.directory"] is True
        assert specs[0]["onyo.path.name"] == p
        assert specs[0]["onyo.path.parent"] == Path(".")

def test_get_template_directory(onyorepo: OnyoRepo) -> None:
    template_base_dir = Path("packaged_templates")
    # regular, non-empty dir represented as such or as a yaml file specifying this dir and its assets:
    for p in ["template_dir", "template_dir_file"]:
        specs = [s for s in onyorepo.get_templates(template_base_dir / p, recursive=True)]
        assert len(specs) == 4  # Three assets and one explicit dir (it's empty). There are two implicit dirs.
        num_dirs = 0
        num_assets = 0
        for s in specs:
            if s.get("onyo.is.directory"):
                num_dirs += 1
                assert s["onyo.path.parent"] == Path(p) / "subdir"
                assert s["onyo.path.name"] == "empty"
            if s.get("onyo.is.asset"):
                num_assets += 1
                assert "model.name" in s.keys()
                assert (s["model.name"] == "somemodel1" and s["onyo.path.parent"] == Path(p)) or \
                       (s["model.name"] == "somemodel2" and s["onyo.path.parent"] == Path(p)) or \
                       (s["model.name"] == "somemodel3" and s["onyo.path.parent"] == Path(p) / "subdir")
        assert num_dirs == 1
        assert num_assets == 3

def test_get_template_asset_directory(onyorepo: OnyoRepo) -> None:
    template_base_dir = Path("packaged_templates")

    specs = [s for s in onyorepo.get_templates(template_base_dir / "asset_dir", recursive=False)]
    assert len(specs) == 2  # TODO: link issue: depth=0 notion prevents correct non-recursive behavior for asset dirs
    assert specs[0]["onyo.is.directory"] is True
    assert specs[0]["onyo.is.asset"] is True
    assert specs[0]["serial"] == "faux"
    assert specs[0]["standard"] == "DDR4-3200"
    assert "onyo.path.name" not in specs[0]
    assert specs[0]["onyo.path.parent"] == Path(".")

    # recursive
    specs = [s for s in onyorepo.get_templates(template_base_dir / "asset_dir", recursive=True)]
    assert len(specs) == 4  # 1 asset dir, 2 regular assets, and one explicit dir
    num_asset_dirs = 0
    num_dirs = 0
    num_assets = 0
    for s in specs:
        if s.get("onyo.is.asset") and s.get("onyo.is.directory"):
            num_asset_dirs += 1
            assert s["standard"] == "DDR4-3200"
        elif s.get("onyo.is.asset"):
            num_assets += 1
            assert (s["model.name"] == "somemodel1" and s["onyo.path.parent"] == Path("asset_dir")) or \
                   (s["model.name"] == "somemodel3" and s["onyo.path.parent"] == Path("asset_dir") / "subdir")
        else:
            num_dirs += 1
            assert s["onyo.is.directory"] is True
            assert s["onyo.path.parent"] == Path("asset_dir") / "subdir"
            assert s["onyo.path.name"] == "empty"
    assert num_asset_dirs == 1
    assert num_assets == 2
    assert num_dirs == 1

@pytest.mark.inventory_dirs(Path('a/test/directory/structure/'),
                            Path('another/dir/'))
def test_validate_anchors(onyorepo) -> None:
    """``validate_anchors()`` returns True when all dirs have an `.anchor` file, and otherwise False."""

    # Must be true for valid repository
    assert onyorepo.validate_anchors()

    for d in onyorepo.test_annotation['dirs']:
        # Delete an .anchor, commit changes, re-validate
        anchor = (d / ANCHOR_FILE_NAME)
        anchor.unlink()
        onyorepo.commit(anchor, "TEST")
        # Must return False, because an .anchor is missing
        assert not onyorepo.validate_anchors()


@pytest.mark.gitrepo_contents((Path('.gitignore'), "idea/"),
                              (Path("subdir") / ".gitignore", "i_*"),
                              (Path(IGNORE_FILE_NAME), "*.pdf\ndocs/"),
                              (Path("subdir") / IGNORE_FILE_NAME, "untracked*\n"),
                              (Path("dirty"), ""),
                              (Path("i_dirty"), ""),
                              (Path("idea") / "something", "blubb"),
                              (Path("some.pdf"), "bla"),
                              (Path("subdir") / "another.pdf", "content"),
                              (Path("subdir") / "i_untracked", ""),
                              (Path("subdir") / "regular", "whatever"),
                              (Path("subdir") / "subsub" / "untracked_som.txt", ""),
                              (Path("docs") / "regular", "whatever")
                              )
@pytest.mark.inventory_assets(Item(type="atype",
                                   make="amake",
                                   model="amodel",
                                   serial=1,
                                   path=Path("subdir") / "atype_amake_amodel.1"))
def test_onyo_ignore(onyorepo) -> None:

    # TODO: This test still has hardcoded stuff from the markers.
    #       Markers and fixture annotation not fit for this yet.
    for a in onyorepo.test_annotation['assets']:
        assert not onyorepo.is_onyo_ignored(a['onyo.path.absolute'])
    for d in onyorepo.test_annotation['dirs']:
        assert not onyorepo.is_onyo_ignored(d)
        assert not onyorepo.is_onyo_ignored(d / ANCHOR_FILE_NAME)
    for f in onyorepo.test_annotation['git'].test_annotation['files']:
        if f.name.endswith('pdf'):
            assert onyorepo.is_onyo_ignored(f)
        elif onyorepo.git.root / 'docs' in f.parents:
            assert onyorepo.is_onyo_ignored(f)
        elif onyorepo.git.root / 'subdir' in f.parents and f.name.startswith("untracked"):
            assert onyorepo.is_onyo_ignored(f)
        else:
            assert not onyorepo.is_onyo_ignored(f)


def test_onyo_auto_message(onyorepo, caplog) -> None:
    """Test configuration ``'onyo.commit.auto-message'``."""

    # default after repo init: True
    assert onyorepo.auto_message

    # test various changes to the config:
    config_to_value = {"false": False,
                       "FaLSe": False,
                       "0": False,
                       "true": True,
                       "TRue": True,
                       "1": True
                       }
    for cfg, val in config_to_value.items():
        onyorepo.set_config("onyo.commit.auto-message", cfg)
        assert onyorepo.auto_message is val

    # invalid config gives warning and uses hardcoded default `True`
    onyorepo.set_config("onyo.commit.auto-message", "invalid value")
    assert onyorepo.auto_message
    assert caplog.text.startswith("WARNING")
    assert "Invalid config value" in caplog.text


@pytest.mark.gitrepo_contents((Path('.gitignore'), "idea/"),
                              (Path("subdir") / ".gitignore", "i_*"),
                              (Path(IGNORE_FILE_NAME), "*.pdf\ndocs/"),
                              (Path("subdir") / IGNORE_FILE_NAME, "untracked*\n"),
                              (Path("idea") / "something", "blubb"),
                              (Path("some.pdf"), "bla"),
                              (Path("subdir") / "another.pdf", "content"),
                              (Path("subdir") / "i_untracked", ""),
                              (Path("subdir") / "subsub" / "untracked_some.txt", ""),
                              (Path("docs") / "regular", "whatever")
                              )
@pytest.mark.inventory_assets(Item(type="atype",
                                   make="amake",
                                   model="amodel",
                                   serial=1,
                                   path=Path("subdir") / "atype_amake_amodel.1"))
@pytest.mark.inventory_dirs(Path('a/test/directory/structure/'),
                            Path('another/dir/'))
@pytest.mark.inventory_templates((TEMPLATE_DIR / "t_dir" / "atemplate", "--\nkey: value\n"))
def test_get_item_paths(onyorepo) -> None:
    assert set(onyorepo.get_item_paths(types=['assets'])) == set(a['onyo.path.absolute'] for a in onyorepo.test_annotation['assets'])
    assert set(onyorepo.get_item_paths(types=['assets'],
                                       include=[onyorepo.template_dir])) == set(onyorepo.test_annotation['templates'])
    assert set(onyorepo.get_item_paths(types=['directories'])) == set(onyorepo.test_annotation['dirs'] + [onyorepo.git.root])

    # listing both types is equivalent to summing of separate calls:
    assert set(onyorepo.get_item_paths(types=['assets', 'directories'])) == set(
        [a['onyo.path.absolute'] for a in onyorepo.test_annotation['assets']] +
        onyorepo.test_annotation['dirs'] + [onyorepo.git.root]
    )

    # Explicitly double-check onyoignored stuff:
    ignored_path = onyorepo.git.root / "subdir" / "subsub" / "untracked_some.txt"
    assert ignored_path not in onyorepo.get_item_paths(types=['assets', 'directories'])
    assert all(onyorepo.git.root / "docs" not in p.parents
               for p in onyorepo.get_item_paths(types=['assets', 'directories']))

    # TODO: Test include/exclude/depth. This is currently only done at higher level (onyo get command).
