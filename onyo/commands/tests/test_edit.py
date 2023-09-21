import os
import subprocess
from pathlib import Path

from onyo.lib.command_utils import get_editor
from onyo.lib import OnyoRepo
from onyo.lib.commands import fsck
import pytest

assets = ['laptop_apple_macbookpro.0',
          'simple/laptop_apple_macbookpro.1',
          's p a/c e s/laptop_apple_macbookpro.2',
          'very/very/very/deep/spe\"c_ial\\ch_ar\'ac.teஞrs'
          ]


@pytest.mark.parametrize('variant', ['local', 'onyo'])
def test_get_editor_git(repo: OnyoRepo, variant: str) -> None:
    """
    Get the editor from git or onyo configs.
    """
    repo.git.set_config('onyo.core.editor', variant, location=variant)

    # test
    editor = get_editor(repo)
    assert editor == variant


def test_get_editor_envvar(repo: OnyoRepo) -> None:
    """
    Get the editor from $EDITOR.
    """
    # verify that onyo.core.editor is not set
    assert not repo.git.get_config('onyo.core.editor')

    # test
    os.environ['EDITOR'] = 'editor'
    assert get_editor(repo) == 'editor'


def test_get_editor_fallback(repo: OnyoRepo) -> None:
    """
    When no editor is set, nano is the fallback.
    """
    # verify that onyo.core.editor is not set
    assert not repo.git.get_config('onyo.core.editor')
    try:
        assert not os.environ['EDITOR']
    except KeyError:
        pass

    # test
    assert get_editor(repo) == 'nano'


def test_get_editor_precedence(repo: OnyoRepo) -> None:
    """
    The order of precedence should be git > onyo > $EDITOR.
    """
    # set locations
    repo.git.set_config('onyo.core.editor', 'local', location='local')
    repo.git.set_config('onyo.core.editor', 'onyo', location='onyo')
    os.environ['EDITOR'] = 'editor'

    # git should win
    assert get_editor(repo) == 'local'

    # onyo should win
    ret = subprocess.run(["git", "config", '--unset', "onyo.core.editor"])
    assert ret.returncode == 0
    assert get_editor(repo) == 'onyo'

    # $EDITOR is all that's left
    ret = subprocess.run(["onyo", "config", '--unset', "onyo.core.editor"])
    assert ret.returncode == 0
    assert get_editor(repo) == 'editor'


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_edit_single_asset(repo: OnyoRepo, asset: str) -> None:
    """
    Test that for different paths it is possible to call `onyo edit` on a single
    asset file.
    """
    os.environ['EDITOR'] = "printf 'key: single_asset' >"

    # test `onyo edit` on a single asset
    ret = subprocess.run(['onyo', '--yes', 'edit', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "+key: single_asset" in ret.stdout
    assert not ret.stderr

    # verify the changes were actually written and the repo is in a clean state:
    assert 'key: single_asset' in Path.read_text(Path(asset))
    fsck(repo)


@pytest.mark.repo_files(*assets)
def test_edit_multiple_assets(repo: OnyoRepo) -> None:
    """
    Test that it is possible to call `onyo edit` with a list of multiple assets
    containing different file names at once.
    """
    os.environ['EDITOR'] = "printf 'key: multiple_assets' >"
    repo_assets = repo.asset_paths

    # test edit for a list of assets all at once
    ret = subprocess.run(['onyo', '--yes', 'edit', *repo_assets],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert ret.stdout.count("+key: multiple_assets") == len(repo_assets)
    assert not ret.stderr

    # verify the changes were saved for all assets and the repository is clean
    for asset in repo_assets:
        assert 'key: multiple_assets' in Path.read_text(asset)
    fsck(repo)


@pytest.mark.repo_files(*assets)
def test_edit_with_user_response(repo: OnyoRepo) -> None:
    """
    Test that without the --yes flag, `onyo edit` requests a user response
    before saving changes.
    """
    os.environ['EDITOR'] = "printf 'key: user_response' >"

    # test edit for a list of assets all at once
    ret = subprocess.run(['onyo', 'edit', *assets],
                         input='y', capture_output=True, text=True)
    assert ret.returncode == 0

    # verify that the user response is requested
    assert "Save changes?" in ret.stdout
    assert not ret.stderr
    fsck(repo)


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_edit_message_flag(repo: OnyoRepo, asset: str) -> None:
    """
    Test that `onyo edit --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    os.environ['EDITOR'] = "printf 'key: value' >"
    msg = "I am here to test the --message flag with spe\"cial\\char\'acteஞrs!"

    # test `onyo edit --message msg`
    ret = subprocess.run(['onyo', '--yes', 'edit', '--message', msg, asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr

    # test that the onyo history does contain the user-defined message
    ret = subprocess.run(['onyo', 'history', '-I', asset],
                         capture_output=True, text=True)
    assert msg in ret.stdout
    fsck(repo)


@pytest.mark.repo_files(*assets)
def test_quiet_flag(repo: OnyoRepo) -> None:
    """
    Test that `onyo edit --yes --quiet` does not print anything.
    """
    os.environ['EDITOR'] = "printf 'key: quiet' >"

    # edit a list of assets all at once
    ret = subprocess.run(['onyo', '--yes', '--quiet', 'edit', *assets],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # verify output is empty
    assert not ret.stdout
    assert not ret.stderr

    # verify the changes were saved for all assets and the repository is clean
    for asset in repo.asset_paths:
        assert 'key: quiet' in Path.read_text(asset)
    fsck(repo)


@pytest.mark.repo_files(*assets)
def test_quiet_errors_without_yes_flag(repo: OnyoRepo) -> None:
    """
    Test that `onyo edit --quiet` does error without --yes flag.
    """
    os.environ['EDITOR'] = "printf 'key: quiet' >"

    # edit a list of assets all at once
    ret = subprocess.run(['onyo', '--quiet', 'edit', *assets],
                         capture_output=True, text=True)

    # verify correct error.
    assert not ret.stdout
    assert ret.returncode == 1
    assert 'The --quiet flag requires --yes.' in ret.stderr
    fsck(repo)


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_edit_discard(repo: OnyoRepo, asset: str) -> None:
    """
    Test that if an asset got correctly changed, but the user answers to the
    "Save changes?" dialog with 'n', that the changes get discarded.
    """
    os.environ['EDITOR'] = "printf 'key: discard' >"

    # change asset with `onyo edit` but don't save it
    ret = subprocess.run(['onyo', 'edit', asset],
                         input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes?" in ret.stdout
    assert "+key: discard" in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr

    # verify that the changes got discarded and the repository is clean afterwards
    assert "key: discard" not in Path.read_text(Path(asset))
    fsck(repo)


@pytest.mark.repo_dirs('simple/', 's p a c e s/', 's p a/c e s/',
                       'very/very/very/deep/')
@pytest.mark.parametrize('no_asset', [
    'simple/.anchor',
    's p a c e s/.anchor',
    's p a/c e s/.anchor',
    'very/very/very/deep/.anchor',
    '.onyo/config',
    '.git/index'
])
def test_edit_protected(repo: OnyoRepo, no_asset: str) -> None:
    """
    Test the error behavior when called on protected files.
    """
    os.environ['EDITOR'] = "printf 'key: NOT_USED' >"

    ret = subprocess.run(['onyo', 'edit', no_asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "is not an asset" in ret.stderr
    assert Path(no_asset).is_file()
    fsck(repo)


@pytest.mark.repo_files('simple/laptop_apple_macbookpro.1')
@pytest.mark.repo_dirs('very/very/very/deep/')
@pytest.mark.parametrize('no_asset', [
    "non_existing_asset.0",
    "simple/laptop_apple_",
    "simple/non_existing_asset.0",
    "very/very/very/deep/non_existing_asset.0"
])
def test_edit_non_existing_file(repo: OnyoRepo, no_asset: str) -> None:
    """
    Test the error behavior when called on non-existing files, that Onyo does
    not create the files, and the repository stays valid.
    """
    os.environ['EDITOR'] = "printf 'key: DOES_NOT_EXIST' >"

    ret = subprocess.run(['onyo', 'edit', no_asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "is not an asset" in ret.stderr
    assert not Path(no_asset).is_file()
    fsck(repo)


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_continue_edit_no(repo: OnyoRepo, asset: str) -> None:
    """
    Test that Onyo detects yaml-errors, and responds correctly if the user
    answers the "continue edit?" dialog with 'n' to discard the changes
    """
    os.environ['EDITOR'] = "printf 'key: YAML: ERROR' >"

    # Change the asset to invalid yaml, and respond 'n' to "further edit" dialog
    ret = subprocess.run(['onyo', 'edit', asset],
                         input='n', capture_output=True, text=True)
    assert ret.returncode == 0
    assert "not updated" in ret.stdout
    assert "has invalid YAML syntax" in ret.stderr

    # Verify that the changes are not written in to the file, and that the
    # repository stays in a clean state
    assert 'YAML: ERROR: STRING' not in Path.read_text(Path(asset))
    fsck(repo)


@pytest.mark.repo_files(*assets)
def test_edit_without_changes(repo: OnyoRepo) -> None:
    """
    Test that onyo not fails when no changes were made
    """
    os.environ['EDITOR'] = "cat"

    # open assets with `cat`, but do not change them
    assets = [str(asset) for asset in repo.asset_paths]
    ret = subprocess.run(['onyo', 'edit', *assets],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    fsck(repo)


@pytest.mark.repo_files(*assets)
@pytest.mark.parametrize('asset', assets)
def test_edit_with_dot_dot(repo: OnyoRepo, asset: str) -> None:
    """
    Check that in an onyo repository it is possible to call `onyo edit` on an
    asset path that contains ".." leading outside and back into the repository.
    """
    os.environ['EDITOR'] = "printf 'key: dot_dot' >"

    # check edit with a path containing a ".." that leads outside the onyo repo
    # and then inside again
    # Note: Strange. That path isn't used with `edit` at all.
    path = Path(f"../{repo.git.root.name}/{asset}")
    assert path.is_file()
    ret = subprocess.run(['onyo', '--yes', 'edit', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "+key: dot_dot" in ret.stdout
    assert not ret.stderr

    # verify that the change did happen and the repository is clean afterwards
    assert 'key: dot_dot' in Path.read_text(path)
    fsck(repo)
