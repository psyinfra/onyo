import subprocess

from onyo.lib import Repo, OnyoInvalidRepoError
import pytest

files = ['laptop_apple_macbookpro',
         'lap top_ap ple_mac book pro']

directories = ['.',
               's p a c e s',
               'r/e/c/u/r/s/i/v/e',
               'overlap/one',
               'overlap/two',
               'very/very/very/deep'
               ]

assets = [f"{d}/{f}.{i}" for f in files for i, d in enumerate(directories)]

content_dict = {"one_key": "one_value",
                "two_key": "two_value",
                "three_key": "three_value"}

content_str = "\n".join([f"{elem}: {content_dict.get(elem)}"
                         for elem in content_dict]) + "\n"

contents = [[x, content_str] for x in assets]


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_cat(repo: Repo, asset: str) -> None:
    """
    Test that a single file is cat successfully, and that stdout matches file
    content.
    """
    ret = subprocess.run(["onyo", "cat", asset], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert content_str == ret.stdout


@pytest.mark.repo_contents(*contents)
def test_cat_multiple_inputs(repo: Repo) -> None:
    """
    Test that multiple files are cat successfully, and that stdout matches file
    content.
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
def test_cat_non_existing_path(repo: Repo, variant: str) -> None:
    """
    Test that cat fails for a path that doesn't exist.
    """
    ret = subprocess.run(['onyo', 'cat', variant], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_files('one_that_exists.test', 'dir/two_that_exists.test')
@pytest.mark.parametrize('variant', [
    ['does_not_exist.test', 'one_that_exists.test', 'dir/two_that_exists.test'],
    ['one_that_exists.test', 'does_not_exist.test', 'dir/two_that_exists.test'],
    ['one_that_exists.test', 'dir/two_that_exists.test', 'does_not_exist.test']]
)
def test_cat_multiple_paths_missing(repo: Repo, variant: list[str]) -> None:
    """
    Test that cat fails with multiple paths if at least one doesn't exist.
    """
    ret = subprocess.run(['onyo', 'cat', *variant], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('directory', directories)
def test_cat_error_with_directory(repo: Repo, directory: str) -> None:
    """
    Test that cat fails if path provided not a file.
    """
    ret = subprocess.run(['onyo', 'cat', directory], capture_output=True, text=True)
    assert ret.returncode == 1
    assert not ret.stdout
    assert ret.stderr


@pytest.mark.repo_contents(*contents)
@pytest.mark.parametrize('asset', assets)
def test_same_target(repo: Repo, asset: str) -> None:
    """
    Test that cat succeeds if the same path is provided more than once.
    """
    ret = subprocess.run(['onyo', 'cat', asset, asset], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == f"{content_str}{content_str}"


@pytest.mark.repo_contents(*[["no_trailing_newline.test",
                              "---\nRAM:\nSize:\nUSB:"]])
@pytest.mark.parametrize('variant', [["no_trailing_newline.test",
                                      "---\nRAM:\nSize:\nUSB:"]])
def test_no_trailing_newline(repo: Repo, variant: list[str]) -> None:
    """
    Test that `onyo cat` outputs the file content exactly, and doesn't add any
    newlines or other characters.
    """
    # test
    ret = subprocess.run(['onyo', 'cat', variant[0]], capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    assert ret.stdout == variant[1]


@pytest.mark.repo_files(*assets)
def test_no_trailing_newline_with_many_empty_assets(repo: Repo) -> None:
    """
    Test that `onyo cat ASSET ASSET [...]` does not print empty lines when given
    a list of empty files.

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
def test_invalid_yaml(repo: Repo, variant: list[str]) -> None:
    """
    Test that `onyo cat` fails for a file with invalid yaml content.
    """
    # check that yaml is invalid
    with pytest.raises(OnyoInvalidRepoError):
        repo.fsck(['asset-yaml'])

    # test
    ret = subprocess.run(['onyo', 'cat', variant[0]],
                         capture_output=True, text=True)
    assert ret.returncode == 1
    assert ret.stderr
    assert not ret.stdout
