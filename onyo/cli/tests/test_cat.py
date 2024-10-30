from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import fsck
from onyo.lib.exceptions import OnyoInvalidRepoError

if TYPE_CHECKING:
    from typing import List

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro']

directories = ['.',
               's p a c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'very/very/very/deep'
               ]

assets: List[str] = [f"{d}/{f}.{i}" for f in files for i, d in enumerate(directories)]

content_dict = {"one_key": "one_value",
                "two_key": "two_value",
                "three_key": "three_value"}

content_str: str = "\n".join([f"{elem}: {content_dict.get(elem)}"
                              for elem in content_dict]) + "\n"

contents: List[List[str]] = [[x, content_str] for x in assets]


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_cat(repo: OnyoRepo, asset: str) -> None:
    r"""
    Single file is cat successfully, and stdout matches file content.
    """
    ret = subprocess.run(["onyo", "cat", asset], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert content_str == ret.stdout


@pytest.mark.repo_contents(*contents)
def test_cat_multiple_inputs(repo: OnyoRepo) -> None:
    r"""
    Multiple files are cat successfully, and stdout matches file content.
    """
    ret = subprocess.run(["onyo", "cat", *assets], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout.count(content_str) == len(assets)


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('variant', ['does_not_exist.test',
                                     's p a c e s/does_not_exist.test',
                                     'r/e/c/u/r/s/i/v/e/does_not_exist.test'
                                     ]
                         )
def test_cat_non_existing_path(repo: OnyoRepo, variant: str) -> None:
    r"""
    Error (2) on path that doesn't exist.
    """
    ret = subprocess.run(['onyo', 'cat', variant], capture_output=True, text=True)
    assert ret.returncode == 2
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_files('one_that_exists.test', 'dir/two_that_exists.test')
@pytest.mark.parametrize('variant', [
    ['does_not_exist.test', 'one_that_exists.test', 'dir/two_that_exists.test'],
    ['one_that_exists.test', 'does_not_exist.test', 'dir/two_that_exists.test'],
    ['one_that_exists.test', 'dir/two_that_exists.test', 'does_not_exist.test']]
)
def test_cat_multiple_paths_missing(repo: OnyoRepo, variant: list[str]) -> None:
    r"""
    Errors (2) with multiple paths when at least one doesn't exist.
    """
    ret = subprocess.run(['onyo', 'cat', *variant], capture_output=True, text=True)
    assert ret.returncode == 2
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('directory', directories)
def test_cat_error_with_directory(repo: OnyoRepo, directory: str) -> None:
    r"""
    Error (2) if path provided is a plain directory.
    """
    ret = subprocess.run(['onyo', 'cat', directory], capture_output=True, text=True)
    assert ret.returncode == 2
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_same_target(repo: OnyoRepo, asset: str) -> None:
    r"""
    Succeed if the same path is provided more than once.
    """
    ret = subprocess.run(['onyo', 'cat', asset, asset], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == f"{content_str}{content_str}"


@pytest.mark.repo_contents(*[["no_trailing_newline.test",
                              "---\nRAM:\nSize:\nUSB:"]])
@pytest.mark.parametrize('variant', [["no_trailing_newline.test",
                                      "---\nRAM:\nSize:\nUSB:"]])
def test_no_trailing_newline(repo: OnyoRepo, variant: list[str]) -> None:
    r"""
    The output matches the file content /exactly/, without spurious newlines,
    formatting, or other characters.
    """
    ret = subprocess.run(['onyo', 'cat', variant[0]], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == variant[1]


@pytest.mark.repo_files(*assets)
def test_no_trailing_newline_with_many_empty_assets(repo: OnyoRepo) -> None:
    r"""
    No empty lines when given a list of empty files.

    Because `onyo cat` uses `print(path.read_text(), end='')` this test
    verifies that empty assets do not print empty new lines.
    """
    ret = subprocess.run(['onyo', 'cat', *assets], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert not ret.stdout


@pytest.mark.repo_contents(["bad_yaml_file.test", "I: \nam:bad:\nbad:yaml\n"])
@pytest.mark.parametrize('variant',
                         [["bad_yaml_file.test", "I: \nam:bad:\nbad:yaml\n"]])
def test_invalid_yaml(repo: OnyoRepo, variant: list[str]) -> None:
    r"""
    Invalid content prints to stdout, error message to stderr, and exit 1.
    """

    # check that yaml is invalid
    with pytest.raises(OnyoInvalidRepoError):
        fsck(repo, ['asset-yaml'])

    # test
    ret = subprocess.run(['onyo', 'cat', variant[0]],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert "YAML validation" in ret.stderr
    assert variant[0] in ret.stderr
    assert variant[1] in ret.stdout
