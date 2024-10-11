import os
import subprocess
from pathlib import Path

import pytest

from onyo.lib.onyo import OnyoRepo

assets = [['laptop_apple_macbookpro.0',
           "type: laptop\nmake: apple\nmodel:\n  name: macbookpro\nserial: 0"],
          ['simple/laptop_apple_macbookpro.1',
           "type: laptop\nmake: apple\nmodel:\n  name: macbookpro\nserial: 1"],
          ['s p a/c e s/laptop_apple_macbookpro.2',
           "type: laptop\nmake: apple\nmodel:\n  name: macbookpro\nserial: 2"],
          ['very/very/very/deep/spe\"c_ial\\ch_ar\'ac.teஞrs',
           "type: spe\"c\nmake: ial\\ch\nmodel:\n  name: ar\'ac\nserial: teஞrs"],
          ]


@pytest.mark.parametrize('variant', ['local', 'onyo'])
def test_get_editor_onyo(repo: OnyoRepo, variant: str) -> None:
    r"""
    Get the editor from onyo configuration.
    """
    repo.set_config('onyo.core.editor', variant, location=variant)

    # test
    editor = repo.get_editor()
    assert editor == variant


def test_get_editor_git(repo: OnyoRepo) -> None:
    r"""
    Get the editor from git configuration
    """
    repo.set_config('core.editor', 'git-edit', location='local')
    assert "git-edit" in (repo.git.root / '.git' / 'config').read_text()
    editor = repo.get_editor()
    assert editor == "git-edit"


def test_get_editor_envvar(repo: OnyoRepo) -> None:
    r"""
    Get the editor from $EDITOR.
    """
    # verify that onyo.core.editor is not set
    assert not repo.get_config('onyo.core.editor')

    # test
    os.environ['EDITOR'] = 'editor'
    assert repo.get_editor() == 'editor'


def test_get_editor_fallback(repo: OnyoRepo) -> None:
    r"""
    When no editor is set, nano is the fallback.
    """
    # verify that onyo.core.editor is not set
    assert not repo.get_config('onyo.core.editor')
    try:
        assert not os.environ['EDITOR']
    except KeyError:
        pass

    # test
    assert repo.get_editor() == 'nano'


def test_get_editor_precedence(repo: OnyoRepo) -> None:
    r"""
    The order of precedence should be git > onyo > $EDITOR.
    """
    # set locations
    repo.set_config('onyo.core.editor', 'local', location='local')
    # Use onyo-config to also commit and not end up with a modified worktree here:
    subprocess.run(["onyo", "config", '--add', "onyo.core.editor", "onyo"])
    os.environ['EDITOR'] = 'editor'

    # git should win
    assert repo.get_editor() == 'local'

    # onyo should win
    ret = subprocess.run(["git", "config", '--unset', "onyo.core.editor"])
    assert ret.returncode == 0
    assert repo.get_editor() == 'onyo'

    # $EDITOR is all that's left
    ret = subprocess.run(["onyo", "config", '--unset', "onyo.core.editor"])
    assert ret.returncode == 0
    assert repo.get_editor() == 'editor'


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [a[0] for a in assets])
def test_edit_single_asset(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that for different paths it is possible to call `onyo edit` on a single
    asset file.
    """
    edit_str = "key: single_asset\nnested:\n  some: value"
    os.environ['EDITOR'] = f"printf '{edit_str}' >>"

    # test `onyo edit` on a single asset
    ret = subprocess.run(['onyo', '--yes', 'edit', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert all(f"+{line}" in ret.stdout for line in edit_str.splitlines())
    assert not ret.stderr

    # verify the changes were actually written and the repo is in a clean state:
    assert edit_str in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()

    # add a comment
    comment_str = edit_str.splitlines()[-1] + " # a comment"
    os.environ['EDITOR'] = f"sed -i \"s/{edit_str.splitlines()[-1]}/{comment_str}/g\" "

    # test `onyo edit` on a single asset
    ret = subprocess.run(['onyo', '--yes', 'edit', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert f"+{comment_str}" in ret.stdout
    assert f"-{edit_str.splitlines()[-1]}" in ret.stdout
    assert not ret.stderr

    # verify the changes were actually written and the repo is in a clean state:
    assert comment_str in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_edit_multiple_assets(repo: OnyoRepo) -> None:
    r"""
    Test that it is possible to call `onyo edit` with a list of multiple assets
    containing different file names at once.
    """
    os.environ['EDITOR'] = "printf 'key: multiple_assets' >>"
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
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_edit_with_user_response(repo: OnyoRepo) -> None:
    r"""
    Test that without the --yes flag, `onyo edit` requests a user response
    before saving changes.
    """
    os.environ['EDITOR'] = "printf 'key: user_response' >>"

    # abort command
    input_string = 'a'
    ret = subprocess.run(['onyo', 'edit', *repo.asset_paths],
                         input=input_string, capture_output=True, text=True)
    assert "Accept changes" in ret.stdout
    assert "Save changes?" not in ret.stdout  # we don't get to the final confirmation
    assert "interrupted" in ret.stderr
    assert ret.returncode == 1

    # test edit for a list of assets all at once
    input_string = '\n'.join(
        'y' for i in range(len(repo.asset_paths) + 1))  # confirm per asset + summary
    ret = subprocess.run(['onyo', 'edit', *repo.asset_paths],
                         input=input_string, capture_output=True, text=True)
    assert ret.returncode == 0

    # verify that the user response is requested
    assert "Save changes?" in ret.stdout
    assert not ret.stderr
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [a[0] for a in assets])
def test_edit_message_flag(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that `onyo edit --message msg` overwrites the default commit message
    with one specified by the user containing different special characters.
    """
    os.environ['EDITOR'] = "printf 'key: value' >>"
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
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_quiet_flag(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo edit --yes --quiet` does not print anything.
    """
    os.environ['EDITOR'] = "printf 'key: quiet' >>"

    # edit a list of assets all at once
    ret = subprocess.run(['onyo', '--yes', '--quiet', 'edit', *repo.asset_paths],
                         capture_output=True, text=True)
    assert ret.returncode == 0

    # verify output is empty
    assert not ret.stdout
    assert not ret.stderr

    # verify the changes were saved for all assets and the repository is clean
    for asset in repo.asset_paths:
        assert 'key: quiet' in Path.read_text(asset)
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_quiet_errors_without_yes_flag(repo: OnyoRepo) -> None:
    r"""
    Test that `onyo edit --quiet` does error without --yes flag.
    """
    os.environ['EDITOR'] = "printf 'key: quiet' >>"

    # edit a list of assets all at once
    ret = subprocess.run(['onyo', '--quiet', 'edit', *repo.asset_paths],
                         capture_output=True, text=True)

    # verify correct error.
    assert not ret.stdout
    assert ret.returncode == 1
    assert 'The --quiet flag requires --yes.' in ret.stderr
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [a[0] for a in assets])
def test_edit_discard(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that if an asset got correctly changed, but the user answers to the
    "Save changes?" dialog with 'n', that the changes get discarded.
    """
    os.environ['EDITOR'] = "printf 'key: discard' >>"

    # change asset with `onyo edit` but don't save it
    input_string = 'y\nn'  # 1. stop editing via 'y', 2. discard changes
    ret = subprocess.run(['onyo', 'edit', asset],
                         input=input_string, capture_output=True, text=True)
    assert ret.returncode == 0
    assert "Save changes?" in ret.stdout
    assert "+key: discard" in ret.stdout
    assert "No assets updated." in ret.stdout
    assert not ret.stderr

    # verify that the changes got discarded and the repository is clean afterwards
    assert "key: discard" not in Path.read_text(Path(asset))
    assert repo.git.is_clean_worktree()


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
    r"""
    Test the error behavior when called on protected files.
    """
    os.environ['EDITOR'] = "printf 'key: NOT_USED' >>"

    ret = subprocess.run(['onyo', 'edit', no_asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "The following paths are not assets" in ret.stderr
    assert Path(no_asset).is_file()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_dirs('very/very/very/deep/')
@pytest.mark.parametrize('no_asset', [
    "non_existing_asset.0",
    "simple/laptop_apple_",
    "simple/non_existing_asset.0",
    "very/very/very/deep/non_existing_asset.0"
])
def test_edit_non_existing_file(repo: OnyoRepo, no_asset: str) -> None:
    r"""
    Test the error behavior when called on non-existing files, that Onyo does
    not create the files, and the repository stays valid.
    """
    os.environ['EDITOR'] = "printf 'key: DOES_NOT_EXIST' >>"

    ret = subprocess.run(['onyo', 'edit', no_asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert "The following paths are not assets" in ret.stderr
    assert not Path(no_asset).is_file()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [a[0] for a in assets])
def test_continue_edit_no(repo: OnyoRepo, asset: str) -> None:
    r"""
    Test that Onyo detects yaml-errors, and responds correctly if the user
    answers the "abort command?" dialog with 'a' to discard the changes
    """
    os.environ['EDITOR'] = "printf 'key: YAML: ERROR' >>"

    # Change the asset to invalid yaml, and respond 'y' to "cancel edit" dialog
    ret = subprocess.run(['onyo', 'edit', asset],
                         input='a',
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Invalid YAML" in ret.stderr  # YAML error reported

    # Verify that the changes are not written in to the file, and that the
    # repository stays in a clean state
    assert 'YAML: ERROR' not in Path(asset).read_text()
    assert repo.git.is_clean_worktree()

    # same test, but this time use `--yes` to issue the default answer (despite not being "yes")
    ret = subprocess.run(['onyo', '--yes', 'edit', asset],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert "Invalid YAML" in ret.stderr  # YAML error reported

    # Verify that the changes are not written in to the file, and that the
    # repository stays in a clean state
    assert 'YAML: ERROR' not in Path(asset).read_text()
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
def test_edit_without_changes(repo: OnyoRepo) -> None:
    r"""
    Test that onyo does not fail when no changes were made.
    This still requires a confirmation after editing an asset.
    """
    os.environ['EDITOR'] = "cat"

    # open assets with `cat`, but do not change them
    ret = subprocess.run(['onyo', '--yes', 'edit'] + [str(asset) for asset in repo.asset_paths],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert repo.git.is_clean_worktree()


@pytest.mark.repo_contents(*assets)
@pytest.mark.parametrize('asset', [a[0] for a in assets])
def test_edit_with_dot_dot(repo: OnyoRepo, asset: str) -> None:
    r"""
    Check that in an onyo repository it is possible to call `onyo edit` on an
    asset path that contains ".." leading outside and back into the repository.
    """
    os.environ['EDITOR'] = "printf 'key: dot_dot' >>"

    # check edit with a path containing a ".." that leads outside the onyo repo
    # and then inside again
    path = Path(f"../{repo.git.root.name}/{asset}")
    assert path.is_file()
    ret = subprocess.run(['onyo', '--yes', 'edit', str(path)],
                         capture_output=True, text=True)
    assert ret.returncode == 0
    assert "+key: dot_dot" in ret.stdout
    assert not ret.stderr

    # verify that the change did happen and the repository is clean afterwards
    assert 'key: dot_dot' in Path.read_text(path)
    assert repo.git.is_clean_worktree()
