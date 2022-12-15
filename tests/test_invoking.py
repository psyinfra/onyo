import os
import subprocess
import logging
import pytest
from pathlib import Path

logging.basicConfig()
log = logging.getLogger('onyo')


def run_cmd(cmd, input_str=None):
    ret = subprocess.run(cmd,
                         capture_output=True,
                         input=input_str,
                         shell=True,
                         text=True)

    # if it errored, return it
    if ret.stderr:
        log.info(f"{cmd} {ret.stderr}")
        return ret.stderr.rstrip("\n")

    log.info(f"{cmd} {ret.stdout}")
    return ret.stdout.rstrip("\n")


def read_reference(ref_file, replace_str=''):
    """
    Return the contents of the reference file, with trailing newlines stripped,
    and any replacement text applied

    Accepts the reference file and (optionally) text to swap with the <replace>
    placeholder.
    """
    contents = Path(ref_file).read_text().rstrip("\n")
    contents = contents.replace("<replace>", replace_str)
    return contents


class TestClass:
    """
    Test a variety of Onyo functions. Each method invokes Onyo from a
    different context (onyo root, -C, etc).
    """
    # the folder for the wished output lies relative to this script:
    ref_dir = Path(Path(__file__).parent, 'reference_output/').resolve()

    test_commands = [
        ("onyo init", "", "init_test.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo mkdir user/", "", "empty_file.txt"),
        ("onyo mkdir 'user 2/'", "", "empty_file.txt"),
        ("onyo mkdir shelf/", "", "empty_file.txt"),
        ("onyo mkdir 'trash bin/' delete_me", "", "empty_file.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.1", "", "new.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.2", "", "new.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.3", "", "new.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.4", "", "new.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.5", "", "new.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.6", "", "new.txt"),
        ("onyo new --yes shelf/laptop_apple_macbookpro.7", "", "new.txt"),
        ("onyo new --yes trash\\ bin/this_device_is\\ very.good", "", "new.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo rm shelf/laptop_apple_macbookpro.7", "y", "delete_device.txt"),
        ("onyo mv -q -y shelf/laptop_apple_macbookpro.2 user/", "", "empty_file.txt"),
        ("onyo mv -q -y shelf/laptop_apple_macbookpro.3 user/laptop_apple_macbookpro.3", "", "empty_file.txt"),
        ("onyo mv -q -y user/* 'user 2/'", "", "empty_file.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo mv -q -y shelf/laptop_apple_macbookpro.4 user/", "", "empty_file.txt"),
        ("onyo mv -q -y shelf/laptop_apple_macbookpro.5 user/", "", "empty_file.txt"),
        ("onyo mv -q -y shelf/laptop_apple_macbookpro.6 user/", "", "empty_file.txt"),
        ("onyo mv -q -y 'user 2' 'no user'", "", "empty_file.txt"),
        ("onyo rm -q -y delete_me/", "", "empty_file.txt"),
        ("onyo set --recursive RAM=10", "y", "set_recursive.txt"),
        ("onyo set RAM=20,CPU=vier,USB='None',var='str ing' 'trash bin/this_device_is very.good'", "y", "set_device_good.txt"),
        ("onyo set RAM=50,USB=3 shelf/laptop_apple_macbookpro.1", "y", "set_shelf_laptop.txt"),
        ("onyo cat 'trash bin/this_device_is very.good' shelf/laptop_apple_macbookpro.1", "", "cat_output.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo tree", "", "test_tree_output.txt"),
    ]

    @pytest.mark.parametrize("command, input_str, ref_file", test_commands)
    def test_root_of_repo(self, command, input_str, ref_file):
        """
        Test from the root of the onyo repository.
        """
        ref_file = self.ref_dir.joinpath('root_of_repo/', ref_file)
        test_dir = Path("root_of_repo").resolve()
        test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(test_dir)

        # rm tests use a different replacement text
        if "onyo rm" in command:
            replace_str = command.replace("onyo rm ", "")
        elif "onyo new" in command:
            replace_str = command.replace("onyo new --yes ", "").replace("\\ ", " ")
        else:
            replace_str = str(test_dir)

        # run the tests
        assert run_cmd(command, input_str) == read_reference(ref_file, replace_str)

    @pytest.mark.parametrize("command, input_str, ref_file", test_commands)
    def test_C_absolute(self, command, input_str, ref_file):
        """
        Test from outside the repository using: onyo -C </absolute/path/to/repo>
        """
        ref_file = self.ref_dir.joinpath('C_absolute/', ref_file)
        test_dir = Path("C_absolute").resolve()
        test_dir.mkdir(parents=True, exist_ok=True)

        # inject -C into the commands
        command = command.replace("onyo ", f"onyo -C '{test_dir}' ")
        command = command.replace("git ", f"git -C '{test_dir}' ")

        # Globbing is done by the shell, and thus fails when using -C.
        # This is expected and the right behavior. However, we'll expand the
        # glob here in python, so that the assets are in the correct location
        # for subsequent tests, and not deviate from other test runs.
        command = command.replace("user/*", ' '.join(f"'{x}'" for x in test_dir.glob('user/[!.]*')))

        # rm tests use a different replacement text
        if f"onyo -C '{test_dir}' rm" in command:
            replace_str = command.replace(f"onyo -C '{test_dir}' rm ", "")
        elif f"onyo -C '{test_dir}' new" in command:
            replace_str = command.replace(f"onyo -C '{test_dir}' new --yes ", "").replace("\\ ", " ")
        else:
            replace_str = str(test_dir)

        # run the tests
        assert run_cmd(command, input_str) == read_reference(ref_file, replace_str)
