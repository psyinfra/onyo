from pathlib import Path

import pytest

from onyo.lib.onyo import OnyoRepo, OnyoInvalidRepoError


def test_OnyoRepo_instantiation_existing(onyorepo: OnyoRepo) -> None:
    """The OnyoRepo class must instantiate correctly for paths to
    existing repositories.
    """
    new_repo = OnyoRepo(onyorepo.git.root, init=False)
    assert new_repo.git.root.samefile(onyorepo.git.root)


def test_OnyoRepo_instantiation_non_existing(tmp_path: Path) -> None:
    """The OnyoRepo class must instantiate correctly for paths to
    non-existing repositories.
    """
    new_repo = OnyoRepo(tmp_path, init=True)
    assert new_repo.git.root.samefile(tmp_path)
    assert (new_repo.git.root / '.onyo').is_dir()
    assert (new_repo.git.root / '.git').is_dir()
    # assert dirs/files in .onyo/ exist and are cached correctly
    assert all(x in new_repo.git.files for x in [new_repo.dot_onyo / f for f in [
        new_repo.dot_onyo / OnyoRepo.ANCHOR_FILE_NAME,
        new_repo.dot_onyo / OnyoRepo.ONYO_CONFIG.name,
        new_repo.dot_onyo / new_repo.TEMPLATE_DIR.name / OnyoRepo.ANCHOR_FILE_NAME,
        new_repo.dot_onyo / 'validation' / OnyoRepo.ANCHOR_FILE_NAME,
    ]])
    assert new_repo.git.is_clean_worktree()
    new_repo.validate_onyo_repo()
    # a newly initialized repository has just one commit; requesting older ones is not possible
    assert new_repo.git.get_hexsha()
    pytest.raises(ValueError,
                  new_repo.git.get_hexsha,
                  'HEAD~1')


def test_OnyoRepo_incorrect_input_arguments_raise_error(onyorepo: OnyoRepo,
                                                        tmp_path: Path) -> None:
    """The OnyoRepo must raise certain errors for invalid or conflicting arguments.

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


@pytest.mark.inventory_assets(dict(type="asset",
                                   make="for",
                                   model="test",
                                   serial=0,
                                   path=Path('a') / 'test' / 'asset_for_test.0'))
def test_clear_cache(onyorepo) -> None:
    """The function `OnyoRepo.clear_cache()` must allow to empty the cache of
    the OnyoRepo, so that an invalid cache can be re-loaded by a newly call of
    the property.
    """

    # Use arbitrary asset here:
    asset = onyorepo.test_annotation['assets'][0]['path']

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


def test_Repo_generate_auto_message(onyorepo: OnyoRepo) -> None:
    """A generated commit message has to have a header with less then
    80 characters length, and a body with the paths to changed files
    and directories relative to the root of the repository.
    """
    modified = [onyorepo.git.root / 's p a c e s',
                onyorepo.git.root / 'a/new/folder']

    # generate a commit message:
    message = onyorepo.generate_auto_message(
        format_string='TST [{length}]: {modified}',
        length=len(modified),
        modified=modified)

    # root should not be in output
    assert str(onyorepo.git.root) not in message

    # verify all necessary information is in the message:
    assert f'TST [{len(modified)}]: ' in message


@pytest.mark.gitrepo_contents((Path('a/test/asset_for_test.0'), ""))
def test_is_onyo_path(onyorepo) -> None:
    """Verify that `OnyoRepo.is_onyo_path()` differentiates correctly between
    paths under `.onyo/` and outside of it.
    """
    # True for the directory `.onyo/` itself
    assert onyorepo.is_onyo_path(onyorepo.dot_onyo)
    # True for the directory `templates` inside of `.onyo/`
    assert onyorepo.is_onyo_path(onyorepo.git.root / OnyoRepo.TEMPLATE_DIR)
    # True for a file inside `.onyo/`
    assert onyorepo.is_onyo_path(onyorepo.git.root / OnyoRepo.TEMPLATE_DIR / 'empty')

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


def test_Repo_get_template(onyorepo: OnyoRepo) -> None:
    """
    The function `OnyoRepo.get_template` returns a dictionary representing
    a template file. If a relative path is specified, it will first look in
    `.onyo/templates/`. A default template can be configured via
    'onyo.new.template'. With no config and no name given, returns an empty dict.
    """
    # Call the function without parameter to get the empty template:
    assert onyorepo.get_template() == dict()

    # from the 'templates' dir, use the filename of each template to find the
    # corresponding template file as a path.
    for path in (onyorepo.git.root / OnyoRepo.TEMPLATE_DIR).iterdir():
        if path.name == OnyoRepo.ANCHOR_FILE_NAME:
            continue

        # specify path as absolute, relative to template dir and relative to CWD (repo root):
        for given_path in [path, path.name, path.relative_to(onyorepo.git.root)]:
            template = onyorepo.get_template(path.name)
            assert isinstance(template, dict)  # allow wrapper?
            if path.name != 'empty':  # TODO: Make issue about removing `empty` file. That's pointless.
                assert template != dict()  # TODO: compare content
            else:
                assert template == dict()

    # verify the correct error response when called with a template name that
    # does not exist
    with pytest.raises(ValueError):
        onyorepo.get_template('I DO NOT EXIST')

    # TODO: test config


@pytest.mark.inventory_dirs(Path('a/test/directory/structure/'),
                            Path('another/dir/'))
def test_Repo_validate_anchors(onyorepo) -> None:
    """
    `OnyoRepo.validate_anchors()` must return True when all existing directories
    have an `.anchor` file, and otherwise False.
    """
    # Must be true for valid repository
    assert onyorepo.validate_anchors()

    for d in onyorepo.test_annotation['dirs']:
        # Delete an .anchor, commit changes, re-validate
        anchor = (d / OnyoRepo.ANCHOR_FILE_NAME)
        anchor.unlink()
        onyorepo.commit(anchor, "TEST")
        # Must return False, because an .anchor is missing
        assert not onyorepo.validate_anchors()


@pytest.mark.gitrepo_contents((Path('.gitignore'), "idea/"),
                              (Path("subdir") / ".gitignore", "i_*"),
                              (Path(OnyoRepo.IGNORE_FILE_NAME), "*.pdf\ndocs/"),
                              (Path("subdir") / OnyoRepo.IGNORE_FILE_NAME, "untracked*\n"),
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
@pytest.mark.inventory_assets(dict(type="atype",
                                   make="amake",
                                   model="amodel",
                                   serial=1,
                                   path=Path("subdir") / "atype_amake_amodel.1"))
def test_onyo_ignore(onyorepo) -> None:

    # TODO: This test still has hardcoded stuff from the markers.
    #       Markers and fixture annotation not fit for this yet.
    for a in onyorepo.test_annotation['assets']:
        assert not onyorepo.is_onyo_ignored(a['path'])
    for d in onyorepo.test_annotation['dirs']:
        assert not onyorepo.is_onyo_ignored(d)
        assert not onyorepo.is_onyo_ignored(d / OnyoRepo.ANCHOR_FILE_NAME)
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
    """Test configuration onyo.commit.auto-message"""

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
