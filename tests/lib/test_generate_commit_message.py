from typing import List

import pytest
from onyo import Repo

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
def test_Repo_generate_commit_message(repo: Repo) -> None:
    """
    A generated commit message has to have a header with less then 80 characters
    length, and a body with the paths to changed files and directories relative
    to the root of the repository.
    """
    # modify the repository with some different commands:
    repo.mkdir(repo.root / 'a' / 'new' / 'folder')
    repo.mv(repo.root / "s p a c e s", repo.root / "a/new/folder")
    repo.set([repo.root], {"one_key": "new_value"},
             dryrun=False, rename=False, depth=0)
    repo.unset([repo.root], ["two_key", "three_key"],
               dryrun=False, quiet=True, depth=0)

    # generate a commit message:
    message = repo.generate_commit_message(cmd="TST")
    header = message.split("\n")[0]
    list_files_changed = message.split("\n\n")[-1]
    assert str(repo.root) not in message

    # verify all necessary information is in the header:
    assert f"TST [{len(repo.files_staged)}]: " in header

    # verify all necessary information is in the body:
    assert "a/new/folder" in list_files_changed
    assert "s p a c e s" in list_files_changed
    assert len(list_files_changed.split("\n")) == len(repo.files_staged)
