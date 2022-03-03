import os
import subprocess
import glob
import logging
import pytest

logging.basicConfig()
logger = logging.getLogger('onyo')


def run_test_cmd(cmd, comment="", input_str=""):
    if comment != "":
        run_process = subprocess.Popen(cmd.split() + [comment],
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    else:
        run_process = subprocess.Popen(cmd.split(),
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    if input_str == "":
        run_output, run_error = run_process.communicate()
    else:
        run_output, run_error = run_process.communicate(input_str)
    # return either the output, or the error to test if it is the right one
    if (run_error != ""):
        logger.info(cmd + " " + run_error)
        return run_error
    else:
        logger.info(cmd + " " + run_output)
    return run_output


def read_file(file):
    file_contents = open(file).readlines()
    file_contents = "".join(file_contents).rstrip("\n")
    return file_contents


def check_output_with_file(command, input_str, file):
    assert read_file(file) == run_test_cmd(command, input_str=input_str).rstrip("\n")


class TestClass:

    test_dir = os.getcwd()

    test_output = "/Users/tkadelka/INM7/onyo/tests/output_goals/"
    test_commands = [
                     ("onyo init", "", test_output + "empty_file.txt"),
                     ("git status", "", test_output + "git_status_working_tree_clean.txt"),
                     ("mkdir shelf/", "", test_output + "empty_file.txt"),
                     ("mkdir user/", "", test_output + "empty_file.txt"),
                     ("mkdir user2/", "", test_output + "empty_file.txt"),
                     ("git status", "", test_output + "git_status_working_tree_clean.txt"),
                     ("onyo new shelf", "laptop\napple\nmacbookpro\n1", test_output + "onyo_new_works.txt"),
                     ("onyo new shelf", "laptop\napple\nmacbookpro\n2", test_output + "onyo_new_works.txt"),
                     ("onyo new shelf", "laptop\napple\nmacbookpro\n3", test_output + "onyo_new_works.txt"),
                     ("git status", "", test_output + "git_status_working_tree_clean.txt"),
                     ("onyo mv shelf/laptop_apple_macbookpro.1 user/", "", test_output + "empty_file.txt"),
                     ("onyo mv --rename shelf/laptop_apple_macbookpro.2 user/laptop_apple_macbookpro.4", "", test_output + "empty_file.txt"),
                     ("onyo mv --rename --force shelf/laptop_apple_macbookpro.3 user/laptop_apple_macbookpro.4", "", test_output + "empty_file.txt"),
                     ("onyo mv " + "user/*" + " user2/", "", test_output + "empty_file.txt"),
                     ("git status", "", test_output + "git_status_working_tree_clean.txt")
                     ]

    # run commands from INSIDE the current test folder (without ONYO_REPOSITORY_DIR)
    @pytest.mark.parametrize("command, input_str, file", test_commands)
    def test_from_inside_dir_without_ONYO_REPOSITORY_DIR(self, command, input_str, file):
        current_test_dir = os.path.join(self.test_dir, "test_1")
        # make sure, that ONYO_REPOSITORY_DIR is unset
        if os.getenv('ONYO_REPOSITORY_DIR') is not None:
            del os.environ['ONYO_REPOSITORY_DIR']
        # create the test folder and go into it
        if not os.path.isdir(current_test_dir):
            run_test_cmd("mkdir " + current_test_dir)
        os.chdir(current_test_dir)
        # Test-specific changes:
        # onyo mv user/* needs to expand
        command = command.replace("user/*", " ".join(glob.glob("user/*")))
        # run actual test
        check_output_with_file(command, input_str, file)

    # run commands from INSIDE the current test folder (with ONYO_REPOSITORY_DIR)
    @pytest.mark.parametrize("command, input_str, file", test_commands)
    def test_from_inside_dir_with_ONYO_REPOSITORY_DIR(self, command, input_str, file):
        current_test_dir = os.path.join(self.test_dir, "test_2")
        # make sure, that ONYO_REPOSITORY_DIR is in the folder
        os.environ['ONYO_REPOSITORY_DIR'] = current_test_dir
        if not os.path.isdir(current_test_dir):
            run_test_cmd("mkdir " + current_test_dir)
        os.chdir(current_test_dir)
        # Test-specific changes:
        # onyo mv user/* needs to expand
        command = command.replace("user/*", " ".join(glob.glob("user/*")))
        # run actual test
        check_output_with_file(command, input_str, file)

    # run commands from OUTSIDE the current test folder (with ONYO_REPOSITORY_DIR)
    @pytest.mark.parametrize("command, input_str, file", test_commands)
    def test_from_outside_dir_with_ONYO_REPOSITORY_DIR(self, command, input_str, file):
        current_test_dir = os.path.join(self.test_dir, "test_3")
        os.environ['ONYO_REPOSITORY_DIR'] = current_test_dir
        if not os.path.isdir(current_test_dir):
            run_test_cmd("mkdir " + current_test_dir)
        # this must be NOT ONYO_REPOSITORY_DIR, but e.g. the main test directory
        os.chdir(self.test_dir)
        # Test-specific changes:
        command = command.replace("user/*", " ".join(glob.glob(os.path.join(current_test_dir + "/user/*"))))
        command = command.replace(current_test_dir + "/", "")
        command = command.replace("mkdir ", "mkdir " + current_test_dir + "/")
        command = command.replace("git status", "git -C " + current_test_dir + " status")
        check_output_with_file(command, input_str, file)

    # tests the complete directory, all test-folders, for there structure
    def test_onyo_tree(self):
        test_tree_output = os.path.join(self.test_output, "test_tree_output.txt")
        test_tree_cmd = "onyo tree ."
        os.chdir(self.test_dir)
        check_output_with_file(test_tree_cmd, "", test_tree_output)
