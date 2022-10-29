import logging
import sys
import shutil
from pathlib import Path

from onyo.lib import Repo, OnyoInvalidRepoError
from onyo.commands.edit import edit_asset, get_editor


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


def run_onyo_new(directory, template, interactive, repo: Repo):
    """
    Read a new asset name, check it for uniqueness and validity, create the
    asset (from a template if one was given), edit the new asset (if not
    suppressed with flag) and stage it with git.

    Returns the newly created asset's filename on success.
    """

    new_asset = Path(directory, create_filename(repo))
    temp_asset = Path(repo.root, ".onyo/temp/", new_asset.name)

    template = Path(template).resolve()
    if template.is_file():
        shutil.copyfile(template, temp_asset)
    else:
        log.error(f"'{template}' does not exist.")
        sys.exit(1)

    if new_asset.exists():
        log.error(f"'{new_asset}' asset already exists.")
        sys.exit(1)

    successful = True
    if interactive:
        editor = get_editor(repo)
        successful = edit_asset(editor, temp_asset)

    # add file to git
    if not successful:
        print(f"No new asset '{new_asset.relative_to(repo.root)}' created.")
        sys.exit(1)

    shutil.move(temp_asset, new_asset)
    repo.add(new_asset)
    return new_asset


def create_filename(repo):
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
                word = repo.generate_faux_serials().pop()
            except ValueError as e:
                print(e, file=sys.stderr)
                sys.exit(1)
        words.append(word)
    filename = words[0] + "_" + words[1] + "_" + words[2] + "." + words[3]

    # check if the new asset name is actually unique in onyo repository
    for asset in repo.assets:
        if filename == asset.name:
            log.info(f"'{filename}' exists already in '{asset}'\nCreate a new filename:")
            return create_filename(repo)
    return filename


def sanitize_paths(directory, template, repo):
    """
    Check and normalize the directory and template for the creation of a new
    asset.

    Returns the absolute path of the directory and of the template on success.
    """
    directory = Path(repo.root, directory).resolve()
    if not template:
        template = repo.get_config('onyo.new.template')

    template = Path(repo.root, ".onyo/templates", template).resolve()

    problem_str = ""
    if not template.is_file():
        problem_str += f"\nTemplate file '{template}' does not exist."
    if not directory.is_dir():
        problem_str += f"\n'{directory}' is not a directory."

    if problem_str:
        log.error(problem_str)
        sys.exit(1)
    return [directory, template]


def new(args, opdir):
    """
    Creates a new ``asset`` in ``directory``. The command opens a dialog that
    asks for the field names defined by the asset name scheme, and after
    creation opens the new ``asset`` file with the editor.

    After the editing is done, the new file will be checked for the validity of
    its YAML syntax and based on the rules in ``.onyo/validation/``.
    """
    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    # set and check paths, identify template
    [directory, template] = sanitize_paths(args.directory, args.template, repo)

    # create file for asset, fill in fields
    created_file = run_onyo_new(directory, template, args.interactive, repo)
    git_filepath = created_file.relative_to(repo.root)

    # commit new asset
    repo.commit(f"new asset: {git_filepath}")
