import os
import subprocess
import glob
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


def read_file(file, test_dir):
    file_contents = open(file).readlines()
    file_contents = "".join(file_contents).rstrip("\n")
    file_contents = file_contents.replace("<test_dir>", str(test_dir))
    return file_contents


def check_output_with_file(command, input_str, file, test_dir):
    assert run_test_cmd(command, input_str=input_str).rstrip("\n") == read_file(file, test_dir)


class TestClass:
    test_dir = Path("tests", "sandbox").resolve()
    test_dir.mkdir(parents=True, exist_ok=True)

    # the folder for the wished output lies relative to this script:
    test_output = Path(Path(__file__).parent, 'output_goals/').resolve()

    test_commands = [
        ("onyo init", "", test_output, "init_test.txt"),
        ("git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo mkdir user/", "", test_output, "empty_file.txt"),
        ("onyo mkdir 'user 2/'", "", test_output, "empty_file.txt"),
        ("onyo mkdir shelf/", "", test_output, "empty_file.txt"),
        ("onyo mkdir 'trash bin/' delete_me", "", test_output, "empty_file.txt"),
        ("git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n1", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n2", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n3", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n4", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n5", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n6", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n7", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive 'trash bin/'", "this\ndevice\nis very\ngood", test_output, "onyo_new_works.txt"),
        ("git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo rm shelf/laptop_apple_macbookpro.7", "y", test_output, "delete_device.txt"),
        ("onyo mv --rename shelf/laptop_apple_macbookpro.2 user/laptop_apple_macbookpro.8", "", test_output, "empty_file.txt"),
        ("onyo mv --rename --force shelf/laptop_apple_macbookpro.3 user/laptop_apple_macbookpro.9", "", test_output, "empty_file.txt"),
        ("onyo mv " + "user/*" + " 'user 2/'", "", test_output, "empty_file.txt"),
        ("git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.4 user/", "", test_output, "empty_file.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.5 user/", "", test_output, "empty_file.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.6 user/", "", test_output, "empty_file.txt"),
        ("onyo mv --rename 'user 2' 'no user'", "", test_output, "empty_file.txt"),
        ("onyo rm -q -y delete_me/", "", test_output, "empty_file.txt"),
        ("onyo set --recursive RAM=10", "y", test_output, "set_recursive.txt"),
        ("onyo set RAM=20,CPU=vier,USB='None',var='str ing' 'trash bin/this_device_is very.good'", "y", test_output, "set_device_good.txt"),
        ("onyo set RAM=50,USB=3 shelf/laptop_apple_macbookpro.1", "y", test_output, "set_shelf_laptop.txt"),
        ("onyo cat 'trash bin/this_device_is very.good' shelf/laptop_apple_macbookpro.1", "", test_output, "cat_output.txt"),
        ("git status", "", test_output, "git_status_working_tree_clean.txt"),
    ]

    # run commands from onyo_root (top level of onyo repository)
    @pytest.mark.parametrize("command, input_str, test_folder, file", test_commands)
    def test_from_inside_dir(self, command, input_str, test_folder, file):
        current_test_dir = Path("test 1").resolve()
        current_test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(current_test_dir)
        # Test-specific changes:
        # onyo mv user/* needs to expand
        command = command.replace("user/*", " ".join(glob.glob("user/*")))
        # run actual test
        if "onyo rm" in command:
            check_output_with_file(command, input_str, test_folder.joinpath('test 1/', file), command.replace("onyo rm ", ""))
        else:
            check_output_with_file(command, input_str, test_folder.joinpath('test 1/', file), current_test_dir)

    # test the folders for test_1 with onyo tree
    def test_onyo_tree_test_1(self):
        test_tree_output = Path(self.test_output, "test 1/test_tree_output.txt")
        test_tree_cmd = "onyo -C 'test 1/' tree"
        check_output_with_file(test_tree_cmd, "", test_tree_output, self.test_dir)

    # run commands from outside onyo_root with "onyo -C <test_dir> "
    @pytest.mark.parametrize("command, input_str, test_folder, file", test_commands)
    def test_from_outside_dir(self, command, input_str, test_folder, file):
        current_test_dir = Path("test 2").resolve()
        current_test_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(current_test_dir.parent)
        # Test-specific changes:
        # onyo mv user/* needs to expand
        command = command.replace("user/*", "\"" + "\" \"".join(glob.glob(os.path.join(current_test_dir, "user/*"))) + "\"")
        # instead from testdir, run commands with -C
        command = command.replace("onyo ", "onyo -C '" + str(current_test_dir) + "' ")
        command = command.replace("git ", "git -C '" + str(current_test_dir) + "' ")
        # run actual test
        if "onyo -C '" + str(current_test_dir) + "' rm" in command:
            check_output_with_file(command, input_str, test_folder.joinpath('test 2/', file), command.replace("onyo -C '" + str(current_test_dir) + "' rm ", ""))
        else:
            check_output_with_file(command, input_str, test_folder.joinpath('test 2/', file), current_test_dir)

    # tests the complete directory, all test-folders, for there structure
    def test_onyo_tree_test_2(self):
        test_tree_output = Path(self.test_output, "test 2/test_tree_output.txt")
        test_tree_cmd = "onyo -C 'test 2/' tree"
        check_output_with_file(test_tree_cmd, "", test_tree_output, self.test_dir)
