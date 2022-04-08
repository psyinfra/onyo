import os
import subprocess
import glob
import logging
import pytest
import shlex

logging.basicConfig()
logger = logging.getLogger('onyo')


def run_test_cmd(cmd, comment="", input_str=""):
    if comment != "":
        run_process = subprocess.Popen(shlex.split(cmd) + [comment],
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    else:
        run_process = subprocess.Popen(shlex.split(cmd),
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


def read_file(file, test_dir):
    file_contents = open(file).readlines()
    file_contents = "".join(file_contents).rstrip("\n")
    file_contents = file_contents.replace("<test_dir>", test_dir)
    return file_contents


def check_output_with_file(command, input_str, file, test_dir):
    assert read_file(file, test_dir) == run_test_cmd(command, input_str=input_str).rstrip("\n")


class TestClass:

    test_dir = os.path.join(os.getcwd(), "onyo_tests")
    if not os.path.isdir(test_dir):
        run_test_cmd("mkdir " + test_dir)

    # the folder for the wished output lies relative to this script:
    test_output = os.path.join(os.path.dirname(os.path.realpath(__file__)), "output_goals/")

    test_commands = [
        ("onyo init", "", test_output, "init_test.txt"),
        ("onyo git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo mkdir user/", "", test_output, "empty_file.txt"),
        ("onyo mkdir user\ 2/", "", test_output, "empty_file.txt"),
        ("onyo mkdir shelf/", "", test_output, "empty_file.txt"),
        ("onyo mkdir trash\ bin/", "", test_output, "empty_file.txt"),
        ("onyo git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n1", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n2", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n3", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n4", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n5", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n6", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive shelf", "laptop\napple\nmacbookpro\n7", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive trash\ bin/", "this\ndevice\nis very\ngood", test_output, "onyo_new_works.txt"),
        ("onyo git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo rm shelf/laptop_apple_macbookpro.7", "y", test_output, "delete_device.txt"),
        ("onyo mv --rename shelf/laptop_apple_macbookpro.2 user/laptop_apple_macbookpro.4", "", test_output, "empty_file.txt"),
        ("onyo mv --rename --force shelf/laptop_apple_macbookpro.3 user/laptop_apple_macbookpro.4", "", test_output, "empty_file.txt"),
        ("onyo mv " + "user/*" + " user\ 2/", "", test_output, "empty_file.txt"),
        ("onyo git status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.4 user/", "", test_output, "empty_file.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.5 user/", "", test_output, "empty_file.txt"),
        ("onyo mv shelf/laptop_apple_macbookpro.6 user/", "", test_output, "empty_file.txt"),
        ("onyo mv --rename user\ 2 no\ user", "", test_output, "empty_file.txt"),
        ("onyo git status", "", test_output, "git_status_working_tree_clean.txt"),
    ]

    # run commands from INSIDE the current test folder (without ONYO_REPOSITORY_DIR)
    @pytest.mark.parametrize("command, input_str, test_folder, file", test_commands)
    def test_from_inside_dir_without_ONYO_REPOSITORY_DIR(self, command, input_str, test_folder, file):
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
        if "onyo rm" in command:
            check_output_with_file(command, input_str, test_folder + "/test_1/" + file, os.path.join(current_test_dir, command.replace("onyo rm ", "")))
        else:
            check_output_with_file(command, input_str, test_folder + "/test_1/" + file, current_test_dir)

    # run commands from INSIDE the current test folder (with ONYO_REPOSITORY_DIR)
    @pytest.mark.parametrize("command, input_str, test_folder, file", test_commands)
    def test_from_inside_dir_with_ONYO_REPOSITORY_DIR(self, command, input_str, test_folder, file):
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
        if "onyo rm" in command:
            check_output_with_file(command, input_str, test_folder + "/test_2/" + file, os.path.join(current_test_dir, command.replace("onyo rm ", "")))
        else:
            check_output_with_file(command, input_str, test_folder + "/test_2/" + file, current_test_dir)

    # run commands from OUTSIDE the current test folder (with ONYO_REPOSITORY_DIR)
    @pytest.mark.parametrize("command, input_str, test_folder, file", test_commands)
    def test_from_outside_dir_with_ONYO_REPOSITORY_DIR(self, command, input_str, test_folder, file):
        current_test_dir = os.path.join(self.test_dir, "test_3")
        os.environ['ONYO_REPOSITORY_DIR'] = current_test_dir
        if not os.path.isdir(current_test_dir):
            run_test_cmd("mkdir " + current_test_dir)
        # this must be NOT ONYO_REPOSITORY_DIR, but e.g. the main test directory
        os.chdir(self.test_dir)
        # Test-specific changes:
        command = command.replace("user/*", " ".join(glob.glob(os.path.join(current_test_dir + "/user/*"))))
        command = command.replace(current_test_dir + "/", "")
        if "onyo rm" in command:
            check_output_with_file(command, input_str, test_folder + "/test_3/" + file, os.path.join(current_test_dir, command.replace("onyo rm ", "")))
        else:
            check_output_with_file(command, input_str, test_folder + "/test_3/" + file, current_test_dir)

    # run commands from OUTSIDE the current test folder, but with relative paths
    rel_path_test_commands = [
        ("onyo init test_4", "", test_output, "init_test.txt"),
        ("onyo git -C test_4 status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo mkdir ./test_4/user/", "", test_output, "empty_file.txt"),
        ("onyo mkdir ./test_4/user\ 2/", "", test_output, "empty_file.txt"),
        ("onyo mkdir ./test_4/shelf", "", test_output, "empty_file.txt"),
        ("onyo mkdir ./test_4/trash\ bin", "", test_output, "empty_file.txt"),
        ("onyo git -C test_4 status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo new --non-interactive ./test_4/shelf", "laptop\napple\nmacbookpro\n1", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/shelf", "laptop\napple\nmacbookpro\n2", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/shelf", "laptop\napple\nmacbookpro\n3", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/shelf", "laptop\napple\nmacbookpro\n4", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/shelf", "laptop\napple\nmacbookpro\n5", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/shelf", "laptop\napple\nmacbookpro\n6", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/shelf", "laptop\napple\nmacbookpro\n7", test_output, "onyo_new_works.txt"),
        ("onyo new --non-interactive test_4/trash\ bin/", "this\ndevice\nis very\ngood", test_output, "onyo_new_works.txt"),
        ("onyo git -C test_4 status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo rm test_4/shelf/laptop_apple_macbookpro.7", "y", test_output, "delete_device.txt"),
        ("onyo mv ./test_4/shelf/laptop_apple_macbookpro.1 ./test_4/user/", "", test_output, "empty_file.txt"),
        ("onyo mv --rename ./test_4/shelf/laptop_apple_macbookpro.2 test_4/user/laptop_apple_macbookpro.4", "", test_output, "empty_file.txt"),
        ("onyo mv --rename --force ./test_4/shelf/laptop_apple_macbookpro.3 ./test_4/user/laptop_apple_macbookpro.4", "", test_output, "empty_file.txt"),
        ("onyo mv " + "./test_4/user/*" + " ./test_4/user\ 2/", "", test_output, "empty_file.txt"),
        ("onyo git -C test_4 status", "", test_output, "git_status_working_tree_clean.txt"),
        ("onyo mv test_4/shelf/laptop_apple_macbookpro.4 ./test_4/user/", "", test_output, "empty_file.txt"),
        ("onyo mv test_4/shelf/laptop_apple_macbookpro.5 ./test_4/user/", "", test_output, "empty_file.txt"),
        ("onyo mv test_4/shelf/laptop_apple_macbookpro.6 ./test_4/user/", "", test_output, "empty_file.txt"),
        ("onyo mv --rename ./test_4/user\ 2 ./test_4/no\ user", "", test_output, "empty_file.txt"),
        ("onyo git -C test_4 status", "", test_output, "git_status_working_tree_clean.txt"),
    ]

    @pytest.mark.parametrize("command, input_str, test_folder, file", rel_path_test_commands)
    def test_from_outside_dir_with_relative_path(self, command, input_str, test_folder, file):
        current_test_dir = os.path.join(self.test_dir, "test_4")
        os.chdir(self.test_dir)
        if os.getenv('ONYO_REPOSITORY_DIR') is not None:
            del os.environ['ONYO_REPOSITORY_DIR']
        if not os.path.isdir(current_test_dir):
            run_test_cmd("mkdir " + current_test_dir)
        # Test-specific changes:
        if "*" in command:
            command = command.replace("test_4/user/*", " ".join(glob.glob(os.path.join("test_4/user/*"))))
            command = command.replace("test_4/*", " ".join(glob.glob(os.path.join("test_4/*"))))
        # run actual commands
        if "onyo rm" in command:
            check_output_with_file(command, input_str, test_folder + "/test_4/" + file, os.path.join(current_test_dir, command.replace("onyo rm test_4/", "")))
        else:
            check_output_with_file(command, input_str, test_folder + "/test_4/" + file, current_test_dir)

    # tests the complete directory, all test-folders, for there structure
    def test_onyo_tree(self):
        test_tree_output = os.path.join(self.test_output, "test_tree_output.txt")
        test_tree_cmd = "onyo tree ."
        os.chdir(self.test_dir)
        check_output_with_file(test_tree_cmd, "", test_tree_output, self.test_dir)
