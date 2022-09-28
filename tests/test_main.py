import os
import subprocess
import logging
import pytest
from pathlib import Path

logging.basicConfig()
logger = logging.getLogger('onyo')


def run_test_cmd(cmd, input_str=None):
    ret = subprocess.run(cmd,
                         capture_output=True,
                         input=input_str,
                         shell=True,
                         text=True)

    # if it errored, return it
    if ret.stderr:
        logger.info(f"{cmd} {ret.stderr}")
        return ret.stderr

    logger.info(f"{cmd} {ret.stdout}")
    return ret.stdout


def read_file(ref_file, test_dir):
    contents = Path(ref_file).read_text().rstrip("\n")
    contents = contents.replace("<test_dir>", str(test_dir))
    return contents


def check_output_with_file(command, input_str, ref_file, test_dir):
    assert run_test_cmd(command, input_str=input_str).rstrip("\n") == read_file(ref_file, test_dir)


class TestClass:
    test_dir = Path("tests", "sandbox").resolve()
    test_dir.mkdir(parents=True, exist_ok=True)

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
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n1", "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n2", "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n3", "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n4", "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n5", "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n6", "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n7", "onyo_new_works.txt"),
        ("onyo new --non-interactive 'trash bin/'", "this\ndevice\nis very\ngood", "onyo_new_works.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo rm shelf/laptop_apple_macbookpro.7", "y", "delete_device.txt"),
        ("onyo mv --rename shelf/laptop_apple_macbookpro.2 user/laptop_apple_macbookpro.8", "", "empty_file.txt"),
        ("onyo mv --rename --force shelf/laptop_apple_macbookpro.3 user/laptop_apple_macbookpro.9", "", "empty_file.txt"),
        ("onyo mv " + "user/*" + " 'user 2/'", "", "empty_file.txt"),
        ("git status", "", "git_status_working_tree_clean.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.4 user/", "", "empty_file.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.5 user/", "", "empty_file.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.6 user/", "", "empty_file.txt"),
        ("onyo mv --rename 'user 2' 'no user'", "", "empty_file.txt"),
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
        test_dir = Path("root_of_repo").resolve()
        test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(test_dir)

        # run the tests
        if "onyo rm" in command:
            check_output_with_file(command, input_str, self.ref_dir.joinpath('root_of_repo/', ref_file), command.replace("onyo rm ", ""))
        else:
            check_output_with_file(command, input_str, self.ref_dir.joinpath('root_of_repo/', ref_file), test_dir)

    @pytest.mark.parametrize("command, input_str, ref_file", test_commands)
    def test_C_absolute(self, command, input_str, ref_file):
        """
        Test from outside the repository using: onyo -C </absolute/path/to/repo>
        """
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

        # run the tests
        if f"onyo -C '{test_dir}' rm" in command:
            check_output_with_file(command, input_str, self.ref_dir.joinpath('C_absolute/', ref_file), command.replace(f"onyo -C '{test_dir}' rm ", ""))
        else:
            check_output_with_file(command, input_str, self.ref_dir.joinpath('C_absolute/', ref_file), test_dir)
