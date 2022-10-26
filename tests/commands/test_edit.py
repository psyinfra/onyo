import os
import subprocess
from pathlib import Path

from onyo import commands  # noqa: F401
from onyo.commands.edit import get_editor
import pytest

assets = ['laptop_apple_macbookpro.0',
          'simple/laptop_apple_macbookpro.1',
          's p a c e s/laptop_apple_macbookpro.2',
          's p a/c e s/laptop_apple_macbookpro.3',
          'very/very/very/deep/laptop_apple_macbookpro.4'
          ]


def test_get_editor_git(repo):
    """
    Get the editor from git settings.
    """
    # set the editor
    ret = subprocess.run(["git", "config", "onyo.core.editor", 'vi'],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    assert get_editor(repo.root) == 'vi'


def test_get_editor_onyo(repo):
    """
    Get the editor from onyo settings.
    """
    # set the editor
    ret = subprocess.run(["onyo", "config", "onyo.core.editor", 'vi'],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    assert get_editor(repo.root) == 'vi'


def test_get_config_value_envvar(repo):
    """
    Get the editor from $EDITOR.
    """
    # verify that onyo.core.editor is not set
    ret = subprocess.run(["git", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout
    ret = subprocess.run(["onyo", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout

    os.environ['EDITOR'] = 'vi'
    assert get_editor(repo.root) == 'vi'


def test_get_editor_fallback(repo):
    """
    When no editor is set, nano should be the fallback.
    """
    # verify that onyo.core.editor is not set
    ret = subprocess.run(["git", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout
    ret = subprocess.run(["onyo", "config", "--get", "onyo.core.editor"],
                         capture_output=True, text=True)
    assert not ret.stdout

    assert get_editor(repo.root) == 'nano'


def test_get_editor_precedence(repo):
    """
    The order of precedence should be git > onyo > $EDITOR.
    """
    # set for git
    ret = subprocess.run(["git", "config", "onyo.core.editor", 'first'],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    # set for onyo
    ret = subprocess.run(["onyo", "config", "onyo.core.editor", 'second'],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # set $EDITOR
    os.environ['EDITOR'] = 'third'

    # git should win
    assert get_editor(repo.root) == 'first'

    # onyo should win
    ret = subprocess.run(["git", "config", '--unset', "onyo.core.editor"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert get_editor(repo.root) == 'second'

    # $EDITOR is all that's left
    ret = subprocess.run(["onyo", "config", '--unset', "onyo.core.editor"],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert get_editor(repo.root) == 'third'


@pytest.mark.repo_files('laptop_apple_macbookpro.0',
                        'simple/laptop_apple_macbookpro.1',
                        's p a c e s/laptop_apple_macbookpro.2',
                        's p a/c e s/laptop_apple_macbookpro.3',
                        'very/very/very/deep/laptop_apple_macbookpro.4')
@pytest.mark.parametrize('asset', assets)
def test_edit_single_asset(repo, asset):
    """
    Test that for different paths it is possible to call `onyo edit` on a single
    asset file.
    """
    os.environ['EDITOR'] = "printf 'key: single_asset' >"

    # test `onyo edit` on a single asset
    ret = subprocess.run(['onyo', 'edit', asset], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes?" in ret.stdout
    assert "+key: single_asset" in ret.stdout
    assert not ret.stderr

    # verify the changes were actually written and the repo is in a clean state:
    assert 'key: single_asset' in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files('laptop_apple_macbookpro.0',
                        'simple/laptop_apple_macbookpro.1',
                        's p a c e s/laptop_apple_macbookpro.2',
                        's p a/c e s/laptop_apple_macbookpro.3',
                        'very/very/very/deep/laptop_apple_macbookpro.4')
def test_edit_multiple_assets(repo):
    """
    Test that it is possible to call `onyo edit` with a list of multiple assets
    containing different file names at once.
    """
    os.environ['EDITOR'] = "printf 'key: multiple_assets' >"
    repo_assets = repo.assets

    # test edit for a list of assets all at once
    ret = subprocess.run(['onyo', 'edit'] + list(repo_assets), input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout.count("+key: multiple_assets") == len(repo_assets)
    assert "Save changes?" in ret.stdout
    assert not ret.stderr

    # verify the changes were saved for all assets and the repository is clean
    for asset in repo_assets:
        assert 'key: multiple_assets' in Path.read_text(asset)
    repo.fsck()


@pytest.mark.repo_files('laptop_apple_macbookpro.0',
                        'simple/laptop_apple_macbookpro.1',
                        's p a c e s/laptop_apple_macbookpro.2',
                        's p a/c e s/laptop_apple_macbookpro.3',
                        'very/very/very/deep/laptop_apple_macbookpro.4')
@pytest.mark.parametrize('asset', assets)
def test_edit_discard(repo, asset):
    """
    Test that if an asset got correctly changed, but the user answers to the
    "Save changes?" dialog with 'n', that the changes get discarded.
    """
    os.environ['EDITOR'] = "printf 'key: discard' >"

    # change asset with `onyo edit` but don't save it
    ret = subprocess.run(['onyo', 'edit', asset], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes?" in ret.stdout
    assert "+key: discard" in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr

    # verify that the changes got discarded and the repository is clean afterwards
    assert "key: discard" not in Path.read_text(Path(asset))
    repo.fsck()


no_assets = ['simple/.anchor',
             's p a c e s/.anchor',
             's p a/c e s/.anchor',
             'very/very/very/deep/.anchor',
             '.onyo/config',
             '.git/index'
             ]
@pytest.mark.repo_dirs('simple/', 's p a c e s/', 's p a/c e s/', 'very/very/very/deep/')
@pytest.mark.parametrize('no_asset', no_assets)
def test_edit_protected(repo, no_asset):
    """
    Test the error behavior when called on protected files.
    """
    os.environ['EDITOR'] = "printf 'key: NOT_USED' >"

    ret = subprocess.run(['onyo', 'edit', no_asset], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "is not an asset" in ret.stderr
    assert Path(no_asset).is_file()
    repo.fsck()


no_assets = ["non_existing_asset.0",
             "simple/laptop_apple_",
             "simple/non_existing_asset.0",
             "very/very/very/deep/non_existing_asset.0"
             ]
@pytest.mark.repo_files('simple/laptop_apple_macbookpro.1')
@pytest.mark.repo_dirs('very/very/very/deep/')
@pytest.mark.parametrize('no_asset', no_assets)
def test_edit_non_existing_file(repo, no_asset):
    """
    Test the error behavior when called on non-existing files, that Onyo does
    not create the files, and the repository stays valid.
    """
    os.environ['EDITOR'] = "printf 'key: DOES_NOT_EXIST' >"

    ret = subprocess.run(['onyo', 'edit', no_asset], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "is not an asset" in ret.stderr
    assert not Path(no_asset).is_file()
    repo.fsck()


@pytest.mark.repo_files('laptop_apple_macbookpro.0',
                        'simple/laptop_apple_macbookpro.1',
                        's p a c e s/laptop_apple_macbookpro.2',
                        's p a/c e s/laptop_apple_macbookpro.3',
                        'very/very/very/deep/laptop_apple_macbookpro.4')
@pytest.mark.parametrize('asset', assets)
def test_continue_edit_no(repo, asset):
    """
    Test that Onyo detects yaml-errors, and responds correctly if the user
    answers the "continue edit?" dialog with 'n' to discard the changes
    """
    os.environ['EDITOR'] = "printf 'key: YAML: ERROR' >"

    # Change the asset to invalid yaml, and respond 'n' to "further edit" dialog
    ret = subprocess.run(['onyo', 'edit', asset], input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "not updated" in ret.stdout
    assert "has invalid YAML syntax" in ret.stderr

    # Verify that the changes are not written in to the file, and that the
    # repository stays in a clean state
    assert 'YAML: ERROR: STRING' not in Path.read_text(Path(asset))
    repo.fsck()


@pytest.mark.repo_files('laptop_apple_macbookpro.0',
                        'simple/laptop_apple_macbookpro.1',
                        's p a c e s/laptop_apple_macbookpro.2',
                        's p a/c e s/laptop_apple_macbookpro.3',
                        'very/very/very/deep/laptop_apple_macbookpro.4')
def test_edit_without_changes(repo):
    """
    Test that onyo not fails when no changes were made
    """
    os.environ['EDITOR'] = "cat"

    # open assets with `cat`, but do not change them
    assets = [str(asset) for asset in repo.assets]
    ret = subprocess.run(['onyo', 'edit'] + assets, capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    repo.fsck()


@pytest.mark.repo_files('laptop_apple_macbookpro.0',
                        'simple/laptop_apple_macbookpro.1',
                        's p a c e s/laptop_apple_macbookpro.2',
                        's p a/c e s/laptop_apple_macbookpro.3',
                        'very/very/very/deep/laptop_apple_macbookpro.4')
@pytest.mark.parametrize('asset', assets)
def test_edit_with_dot_dot(repo, asset):
    """
    Check that in an onyo repository it is possible to call `onyo edit` on an
    asset path that contains ".." leading outside and back into the repository.
    """
    os.environ['EDITOR'] = "printf 'key: dot_dot' >"

    # check edit with a path containing a ".." that leads outside the onyo repo
    # and then inside again
    asset = Path(f"../{repo.opdir.name}/{asset}")
    assert asset.is_file()
    ret = subprocess.run(['onyo', 'edit', str(asset)], input='y', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes?" in ret.stdout
    assert "+key: dot_dot" in ret.stdout
    assert not ret.stderr

    # verify that the change did happen and the repository is clean afterwards
    assert 'key: dot_dot' in Path.read_text(asset)
    repo.fsck()
