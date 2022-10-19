import logging
import sys
import shutil
from pathlib import Path

from onyo.lib import Repo, InvalidOnyoRepoError
from onyo.utils import (
    generate_faux_serial,
    get_config_value,
    get_list_of_assets,
    get_git_root,
    edit_file
)

logging.basicConfig()
log = logging.getLogger('onyo')

reserved_characters = ['_', '.']


def read_new_word(word_description):
    """
    Read a new word via user input for the creation of a asset name.
    Checks for the serial field if it contains reserved characters, and checks
    for all fields that they are not empty. If a check is not successful, it
    tries to read the same word again.

    Returns the word on success.
    """
    # read word for field from keyboard
    word = input(word_description)

    # if word contains reserved character, inform and read new word
    for char in reserved_characters:
        if word_description != "<serial>*:" and char in word:
            log.info(f"'{char}' is in list of reserved characters: {reserved_characters}")
            return read_new_word(word_description)

    # if enter pressed without input, read new word
    if len(word) == 0:
        return read_new_word(word_description)
    return word


def run_onyo_new(directory, template, non_interactive, onyo_root, repo):
    """
    Read a new asset name, check it for uniqueness and validity, create the
    asset (from a template if one was given), edit the new asset (if not
    suppressed with flag) and stage it with git.

    Returns the newly created asset's filename on success.
    """
    # create an asset file
    filename = create_filename(onyo_root, template)
    filename = Path(directory, filename).resolve()
    template = Path(template).resolve()

    if filename.exists():
        log.error(f"{filename}' asset already exists.")
        sys.exit(1)
    if template.is_file():
        shutil.copyfile(template, filename)
    else:
        filename.touch()

    # open new file?
    if not non_interactive:
        edit_file(filename, onyo_root, onyo_new=True)

    # add file to git
    repo._git(['add', filename])
    return filename


def create_filename(onyo_root, template):
    """
    Read fields required for an asset name, check the validity of the fields and
    uniqueness of the build-together asset name.

    Returns the new asset name on success.
    """
    words = []
    # build new name, read these words
    for field in ["type", "make", "model", "serial"]:
        word = read_new_word('<' + field + '>*:')
        if field == "serial" and word == "faux":
            try:
                word = generate_faux_serial(onyo_root)
            except ValueError as e:
                print(e)
                sys.exit(1)
        words.append(word)
    filename = words[0] + "_" + words[1] + "_" + words[2] + "." + words[3]

    # check if the new asset name is actually unique in onyo repository
    assets = get_list_of_assets(onyo_root)
    for asset in assets:
        if filename == asset[1]:
            log.info(f"{filename} exists already in {asset[0]}\nCreate a new filename:")
            return create_filename(onyo_root, template)
    return filename


def sanitize_paths(directory, template, onyo_root):
    """
    Check and normalize the directory and template for the creation of a new
    asset.

    Returns the absolute path of the directory and of the template on success.
    """
    directory = Path(onyo_root, directory).resolve()
    if not template:
        template = get_config_value('onyo.new.template', onyo_root)

    template = Path(get_git_root(onyo_root), ".onyo/templates", template).resolve()

    problem_str = ""
    if not template.is_file():
        problem_str += f"\nTemplate file {template} does not exist."
    if not directory.is_dir():
        problem_str += f"\n{directory} is not a directory."

    if problem_str:
        log.error(problem_str)
        sys.exit(1)
    return [directory, template]


def new(args, onyo_root):
    """
    Creates a new ``asset`` in ``directory``. The command opens a dialog that
    asks for the field names defined by the asset name scheme, and after
    creation opens the new ``asset`` file with the editor.

    After the editing is done, the new file will be checked for the validity of
    its YAML syntax and based on the rules in ``.onyo/validation/validation.yaml``.
    """
    try:
        repo = Repo(onyo_root)
        repo.fsck()
    except InvalidOnyoRepoError:
        sys.exit(1)

    # set and check paths, identify template
    [directory, template] = sanitize_paths(args.directory, args.template, onyo_root)

    # create file for asset, fill in fields
    created_file = run_onyo_new(directory, template, args.non_interactive, onyo_root, repo)
    git_filepath = created_file.relative_to(get_git_root(onyo_root))

    # commit new asset
    repo._git(['commit', '-m', f'new asset: {git_filepath}'])
