import subprocess
from pathlib import Path


def test_new_non_interactive(helpers):
    dirs = ['simple',
            's p a c e s',
            's p a/c e s',
            'r/e/c/u/r/s/i/v/e',
            'relative',
            'one',
            'two',
            'three',
            'overlap/one',
            'overlap/two',
            'overlap/three'
            ]
    files = []
    helpers.populate_repo('./', dirs, files)

    # create new asset for all different folders
    for i, directory in enumerate(dirs):
        input_str = f'laptop\napple\nmacbookpro\n{i}'
        file = f'laptop_apple_macbookpro.{i}'
        ret = subprocess.run(['onyo', 'new', '--non-interactive', directory], input=input_str.encode())

        assert ret.returncode == 0
        assert Path(directory, file).exists()


def test_new_non_interactive_with_faux():
    dirs = ['simple',
            's p a c e s',
            's p a/c e s',
            'r/e/c/u/r/s/i/v/e',
            'relative',
            'one',
            'two',
            'three',
            'overlap/one',
            'overlap/two',
            'overlap/three'
            ]
    # create new asset with faux for all different folders
    for d in dirs:
        input_str = 'laptop\napple\nmacbookpro\nfaux'
        ret = subprocess.run(['onyo', 'new', '--non-interactive', d], input=input_str.encode())

        # since the faux are by nature changing, it does not check the existence
        # of the file, just that it exited for all directory names with success
        assert ret.returncode == 0
