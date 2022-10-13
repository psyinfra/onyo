import subprocess
import os
import logging
from pathlib import Path

logging.basicConfig()
logger = logging.getLogger('onyo')
logger.setLevel(logging.INFO)

test_dirs = ['simple',
             's p a c e s',
             's p a/c e s',
             'r/e/c/u/r/s/i/v/e',
             'relative',
             'one',
             'two',
             'three',
             'overlap/one',
             'overlap/two',
             'overlap/three',
             'very/very/very/deep'
             ]


def populate_test_repo(path):
    ret = subprocess.run(['onyo', 'init', path])
    assert ret.returncode == 0

    # enter repo
    original_cwd = Path.cwd()
    os.chdir(path)

    # create dirs
    ret = subprocess.run(['onyo', 'mkdir'] + test_dirs)
    assert ret.returncode == 0

    # return to home
    os.chdir(original_cwd)


def test_new_non_interactive():
    populate_test_repo('./')

    # create new asset for all different folders
    for i, directory in enumerate(test_dirs):
        input_str = f'laptop\napple\nmacbookpro\n{i}'
        file = f'laptop_apple_macbookpro.{i}'
        ret = subprocess.run(['onyo', 'new', '--non-interactive', directory], input=input_str.encode())

        assert ret.returncode == 0
        assert Path(directory, file).exists()


def test_new_non_interactive_with_faux():
    # create new asset with faux for all different folders
    for directory in test_dirs:
        input_str = 'laptop\napple\nmacbookpro\nfaux'
        ret = subprocess.run(['onyo', 'new', '--non-interactive', directory], input=input_str.encode())

        # since the faux are by nature changing, it does not check the existence
        # of the file, just that it exited for all directory names with success
        assert ret.returncode == 0
