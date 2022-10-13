import subprocess
import logging
import os
import sys
import shlex
import shutil
import glob
import yaml
import string
import random
import argparse
from pathlib import Path
from ruamel.yaml import YAML  # pyre-ignore[21]
from onyo import commands
from git import Repo, exc
import textwrap
from onyo._version import __version__

logging.basicConfig()
log = logging.getLogger('onyo')


def run_cmd(cmd, comment=""):
    if comment != "":
        run_process = subprocess.Popen(shlex.split(cmd) + [comment],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    else:
        run_process = subprocess.Popen(shlex.split(cmd),
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       universal_newlines=True)
    run_output, run_error = run_process.communicate()
    if (run_error != ""):
        log.error(run_error)
        sys.exit(1)
    else:
        log.debug(cmd + " " + comment)
    return run_output


def get_git_root(path):
    # first checks if file is in git from current position
    try:
        git_repo = Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        if os.path.isdir(os.path.join(git_root, ".onyo")):
            return git_root
    except (exc.NoSuchPathError, exc.InvalidGitRepositoryError):
        log.error(path + " is no onyo repository.")
        sys.exit(1)
        return git_root


def get_editor(onyo_root):
    """
    Returns the editor, progressing through git, onyo, $EDITOR, and finally
    fallback to "nano".
    """
    editor = None

    # onyo config and git config
    editor = get_config_value('onyo.core.editor', onyo_root)

    # $EDITOR environment variable
    if not editor:
        log.debug("onyo.core.editor is not set.")
        editor = os.environ.get('EDITOR')

    # fallback to nano
    if not editor:
        log.debug("$EDITOR is also not set.")
        editor = 'nano'

    return editor


def generate_faux_serial(onyo_root, faux_length=8):
    """
    Generate a unique faux serial number and verify that it does not appear in
    any other asset file name in any directory of the onyo repository.
    The requested length of faux serial numbers is limited to the interval
    between 1 and 37.

    Returns on success a unique faux serial number which does not appear in any
    other asset file name in any directory of the repository.
    """
    # check that the requested faux serial number has a valid length
    if faux_length < 1 or faux_length > 37:
        raise ValueError("Length of faux serial numbers must be between 1 and 37")

    # generate a new faux serial number until a unique one (which is in no other
    # asset name in the repository) is found, then return it.
    alphanum = string.ascii_letters + string.digits
    list_of_assets = get_list_of_assets(onyo_root)
    faux = "faux" + ''.join(random.choices(alphanum, k=faux_length))
    while True in [faux in asset[1] for asset in list_of_assets]:
        faux = "faux" + ''.join(random.choices(alphanum, k=faux_length))
    return faux


def validate_rule_for_file(file, rule, path_of_rule, original_file, onyo_root):
    asset = ""
    current_error = ""
    yaml = YAML(typ='safe')
    with open(os.path.join(onyo_root, file), "r") as stream:
        try:
            asset = yaml.load(stream)
        except yaml.YAMLError as e:
            print(e)
    for value_field in rule:
        for field in rule[value_field]:
            # value == e.g. RAM
            # field1 == e.g. Type
            # field2 == e.g. str
            field1 = list(field)[0]
            field2 = field[field1]
            if asset and value_field in asset:
                if field1 == "Type":
                    if field2 == "str":
                        if not check_str(asset[value_field]):
                            current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): values for \"" + value_field + "\" must be str, but is \"" + str(asset[value_field]) + "\"\n"
                    elif field2 == "int":
                        if not check_int(asset[value_field]):
                            current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): values for \"" + value_field + "\" must be int, but is \"" + str(asset[value_field]) + "\"\n"
                    elif field2 == "float":
                        if not check_float(asset[value_field]):
                            current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): values for \"" + value_field + "\" must be float, but is \"" + str(asset[value_field]) + "\"\n"
                    else:
                        current_error = current_error + "\t" + os.path.relpath(original_file, onyo_root) + " (" + path_of_rule + "): Type \"" + field2 + "\" is not known.\n"
    # return all errors
    return current_error


def validate_file(file, original_file, onyo_root):
    ru_yaml = YAML(typ='safe')
    error_str = ""
    with open(os.path.join(get_git_root(onyo_root), ".onyo/validation/validation.yaml"), "r") as stream:
        try:
            rules_file = ru_yaml.load(stream)
            if not rules_file:
                rules_file = []
        except yaml.YAMLError as e:
            print(e)
    for path_of_rule in rules_file:
        if error_str != "":
            return error_str
        # when a rule applies to original_file:
        if os.path.join(onyo_root, original_file) in glob.glob(os.path.join(onyo_root, path_of_rule), recursive=True):
            for rule in rules_file[path_of_rule]:
                error_str = error_str + validate_rule_for_file(file, rule, path_of_rule, original_file, onyo_root)
            return error_str
    # give error back for outside handling:
    return error_str


# check for a value from a yaml file, if it is a str or can be formatted to it
def check_str(value):
    try:
        if isinstance(value, str):
            return True
        elif isinstance(str(value), str):
            return True
    except Exception:
        return False


# check for a value from a yaml file, if it is a int or can be formatted to it
def check_int(value):
    try:
        if isinstance(value, int):
            return True
        # this happens in other functions, but should be blocked in check_int,
        # since otherwise all floats will be successfully cast to integer.
        # elif isinstance(int(value), int):
        #    return True
    except Exception:
        return False


# check for a value from a yaml file, if it is a float or can be formatted to it
def check_float(value):
    try:
        if isinstance(value, float):
            return True
        elif isinstance(float(value), float):
            return True
    except Exception:
        return False


def edit_file(file, onyo_root, onyo_new=False):
    """
    Check if the selected editor exists. Check if a file exists, create a copy
    of it in .onyo/temp/ to change with the editor, and check the temp file
    after editing for correct yaml syntax and validity specified by the onyo
    validation file.
    If the asset is not valid, open a dialog to enable to correct the asset, or
    remove the changes.

    Returns True on success.
    """
    editor = get_editor(onyo_root)
    # verify that the editor exists
    if not shutil.which(editor):
        log.error(f"The editor '{editor}' was not found. Exiting.")
        sys.exit(1)

    # verify existence of file to edit
    file = Path(file)
    if not file.is_file():
        log.error(f"{file} does not exist.")
        sys.exit(1)

    # create and edit a temporary file, and if that is valid replace original
    temp_file = Path(get_git_root(onyo_root), ".onyo/temp/", file.name)
    if not temp_file.is_file():
        shutil.copyfile(file, temp_file)
    # When temp-file exists, ask if to use it
    elif temp_file.is_file():
        while True:
            edit_temp = str(input(f"Temporary changes for {file} exist. Continue editing? (y/N) "))
            if edit_temp in ['y', 'Y', 'yes']:
                break
            elif edit_temp == 'n':
                shutil.copyfile(file, temp_file)
                break
    further_editing = 'y'
    while further_editing == 'y':
        # do actual editing:
        os.system(f'{editor} "{temp_file}"')
        # check syntax
        with open(temp_file, "r") as stream:
            try:
                yaml.safe_load(stream)
                problem_str = validate_file(temp_file, file, onyo_root)
                if problem_str == "":
                    shutil.move(temp_file, file)
                else:
                    # TODO: better exception needed
                    raise yaml.YAMLError(f"\nOnyo Validation failed for:\n{problem_str}")
                return
            except yaml.YAMLError as e:
                while True:
                    further_editing = input(f"{e}Continue editing? (y/N) ")
                    if further_editing in ['y', 'Y', 'yes']:
                        break
                    elif further_editing == 'n':
                        output_str = "No changes made."
                        # onyo new should neither create a new file nor a
                        # temp-file, and have a special info message
                        if (onyo_new):
                            Path.unlink(file)
                            output_str = f'No new asset "{file.relative_to(onyo_root)}" created.'
                        Path.unlink(temp_file)
                        log.info(output_str)
                        sys.exit(1)
    return True


def build_git_add_cmd(directory, file):
    return "git -C \"" + directory + "\" add \"" + file + "\""


def get_config_value(name, onyo_root):
    """
    Get the value for a configuration option specified by `name`. git-config is
    checked first, as it is machine-local. The default order of git-config
    checks is retained. If that is empty, then the .onyo/config file is checked.

    Returns a string with the config value on success. None otherwise.
    """
    value = None
    repo = Repo(onyo_root)

    # git-config (with its full stack of locations to check)
    try:
        value = repo.git.config('--get', name)
        log.debug(f"git config acquired '{name}': '{value}'")
    except exc.GitCommandError:
        log.debug(f"git config missed '{name}'")
        pass

    # .onyo/config
    if not value:
        dot_onyo_config = os.path.join(repo.git.rev_parse('--show-toplevel'), '.onyo/config')
        try:
            value = repo.git.config('--get', name, f=dot_onyo_config)
            log.debug(f"onyo config acquired '{name}': '{value}'")
        except exc.GitCommandError:
            log.debug(f"onyo config missed '{name}'")
            pass

    # reset to None if empty
    if not value:
        value = None

    return value


def get_list_of_assets(repo_path):
    """
    Return a list of all assets in an onyo repository.
    """
    return [[x[0][0], Path(x[0][0]).name] for x in Repo(repo_path).index.entries.items()
            if not is_protected_path(x[0][0])]


def is_protected_path(path):
    """
    Checks whether a path contains protected elements (.anchor, .git, .onyo).
    Returns True if it contains protected elements. Otherwise False.
    """
    full_path = Path(path).resolve()

    # protected paths
    for p in full_path.parts:
        if p in ['.anchor', '.git', '.onyo']:
            return True

    return False


def directory(string):
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def file(string):
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def git_config(string):
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def path(string):
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def template(string):
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def setup_parser():
    parser = argparse.ArgumentParser(
        description='A text-based inventory system backed by git.',
        formatter_class=SubcommandHelpFormatter
    )
    parser.add_argument(
        '-C',
        '--onyopath',
        metavar='DIR',
        required=False,
        default=os.getcwd(),
        type=directory,
        help='run as if onyo was started in DIR'
    )
    parser.add_argument(
        '-d',
        '--debug',
        required=False,
        default=False,
        action='store_true',
        help='enable debug logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {version}'.format(version=__version__),
        help="print onyo's version and exit"
    )
    # subcommands
    subcmds = parser.add_subparsers(
        title="commands"
    )
    subcmds.metavar = '<command>'
    #
    # subcommand cat
    #
    cmd_cat = subcmds.add_parser(
        'cat',
        description=textwrap.dedent(commands.cat.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='print the contents of an asset'
    )
    cmd_cat.set_defaults(run=commands.cat)
    cmd_cat.add_argument(
        'asset',
        metavar='ASSET',
        nargs='+',
        type=file,
        help='asset(s) to print'
    )
    #
    # subcommand "config"
    #
    cmd_config = subcmds.add_parser(
        'config',
        description=textwrap.dedent(commands.config.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='set, query, and unset Onyo repository configuration options'
    )
    cmd_config.set_defaults(run=commands.config)
    cmd_config.add_argument(
        'git_config_args',
        metavar='ARGS',
        nargs='+',
        type=git_config,
        help='arguments to set config options in .onyo/config'
    )
    #
    # subcommand "edit"
    #
    cmd_edit = subcmds.add_parser(
        'edit',
        description=textwrap.dedent(commands.edit.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='open asset with a text editor'
    )
    cmd_edit.set_defaults(run=commands.edit)
    cmd_edit.add_argument(
        'asset',
        metavar='ASSET',
        nargs='+',
        type=file,
        help='asset(s) to edit'
    )
    #
    # subcommand "fsck"
    #
    cmd_fsck = subcmds.add_parser(
        'fsck',
        description=textwrap.dedent(commands.fsck.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='verify the integrity and validity of an onyo repository and its contents'
    )
    cmd_fsck.set_defaults(run=commands.fsck)
    #
    # subcommand "history"
    #
    cmd_history = subcmds.add_parser(
        'history',
        description=textwrap.dedent(commands.history.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='show the history of an asset or directory'
    )
    cmd_history.set_defaults(run=commands.history)
    cmd_history.add_argument(
        '-I', '--non-interactive',
        dest='interactive',
        required=False,
        default=True,
        action='store_false',
        help='print the git log instead of opening an interactive tig session'
    )
    cmd_history.add_argument(
        'path',
        metavar='PATH',
        nargs='?',
        type=path,
        help='asset or directory to show the history of'
    )
    #
    # subcommand "init"
    #
    cmd_init = subcmds.add_parser(
        'init',
        description=textwrap.dedent(commands.init.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='initialize an onyo repository'
    )
    cmd_init.set_defaults(run=commands.init)
    cmd_init.add_argument(
        'directory',
        metavar='DIR',
        nargs='?',
        type=directory,
        help='initialize DIR as an onyo repository'
    )
    #
    # subcommand "mkdir"
    #
    cmd_mkdir = subcmds.add_parser(
        'mkdir',
        description=textwrap.dedent(commands.mkdir.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='create a directory (with git anchor)'
    )
    cmd_mkdir.set_defaults(run=commands.mkdir)
    cmd_mkdir.add_argument(
        'directory',
        metavar='DIR',
        nargs='+',
        type=directory,
        help='directory to create'
    )
    #
    # subcommand "mv"
    #
    cmd_mv = subcmds.add_parser(
        'mv',
        description=textwrap.dedent(commands.mv.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='move an asset'
    )
    cmd_mv.set_defaults(run=commands.mv)
    cmd_mv.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='silence messages to stdout (requires the --yes flag)'
    )
    cmd_mv.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='respond "yes" to any prompts'
    )
    cmd_mv.add_argument(
        'source',
        metavar='SOURCE',
        nargs='+',
        type=path,
        help='source ...'
    )
    cmd_mv.add_argument(
        'destination',
        metavar='DEST',
        type=path,
        help='destination'
    )
    #
    # subcommand "new"
    #
    cmd_new = subcmds.add_parser(
        'new',
        description=textwrap.dedent(commands.new.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='create a new asset'
    )
    cmd_new.set_defaults(run=commands.new)
    cmd_new.add_argument(
        '-I', '--non-interactive',
        dest='interactive',
        required=False,
        default=True,
        action='store_false',
        help='do not prompt or open the editor; values must be piped in (e.g. echo "<type>\\n<make>\\n<model>\\n<serial>" | onyo new -I shelf/)'
    )
    cmd_new.add_argument(
        '-t', '--template',
        metavar='TEMPLATE',
        required=False,
        default=None,
        type=template,
        help='the template to seed the new asset'
    )
    cmd_new.add_argument(
        'directory',
        metavar='DIR',
        type=directory,
        help='add a new asset to DIR'
    )
    #
    # subcommand "rm"
    #
    cmd_rm = subcmds.add_parser(
        'rm',
        description=textwrap.dedent(commands.rm.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='delete asset(s) and directories'
    )
    cmd_rm.set_defaults(run=commands.rm)
    cmd_rm.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='silence messages to stdout (requires the --yes flag)'
    )
    cmd_rm.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='respond "yes" to any prompts'
    )
    cmd_rm.add_argument(
        'path',
        metavar='PATH',
        nargs='+',
        type=path,
        help='assets or directories to delete'
    )
    #
    # subcommand "set"
    #
    cmd_set = subcmds.add_parser(
        'set',
        description=textwrap.dedent(commands.set.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='set values in assets'
    )
    cmd_set.set_defaults(run=commands.set)
    cmd_set.add_argument(
        '-d', '--depth',
        metavar='N',
        type=int,
        required=False,
        default=-1,
        help='descend at most "N" levels of directories below the starting-point; used only with --recursive'
    )
    cmd_set.add_argument(
        '-n', "--dry-run",
        required=False,
        default=False,
        action='store_true',
        help='perform a non-interactive trial-run without making any changes'
    )
    cmd_set.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='silence output (requires the --yes flag)'
    )
    cmd_set.add_argument(
        '-R', '--recursive',
        required=False,
        default=False,
        action='store_true',
        help='set values recursively for all assets in a directory'
    )
    cmd_set.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='respond "yes" to any prompts'
    )
    cmd_set.add_argument(
        'keys',
        action=StoreDictKeyPair,
        metavar="KEYS",
        help='key-value pairs to set in assets; multiple pairs can be separated by commas (e.g. key=value,key2=value2)'
    )
    cmd_set.add_argument(
        'path',
        metavar='PATH',
        default='.',
        nargs='*',
        type=path,
        help='assets or directories for which to set values'
    )
    #
    # subcommand shell-completion
    #
    cmd_shell_completion = subcmds.add_parser(
        'shell-completion',
        description=textwrap.dedent(commands.shell_completion.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='shell completion for Onyo, suitable for use with "source"'
    )
    cmd_shell_completion.set_defaults(run=commands.shell_completion)
    cmd_shell_completion.add_argument(
        '-s', '--shell',
        metavar='SHELL',
        required=False,
        default='zsh',
        choices=['zsh'],
        help='shell to generate tab completion for'
    )
    #
    # subcommand "tree"
    #
    cmd_tree = subcmds.add_parser(
        'tree',
        description=textwrap.dedent(commands.tree.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help='print the contents of a directory in a tree-like format'
    )
    cmd_tree.set_defaults(run=commands.tree)
    cmd_tree.add_argument(
        'directory',
        metavar='DIR',
        nargs='*',
        type=directory,
        help='directories to print'
    )
    return parser


def parse_key_values(values):
    results = []
    rest_str = values
    key = ""
    value = ""
    while True:
        if len(rest_str) <= 0:
            break
        next_equal = rest_str.find('=')
        # this happens when `onyo set a=5,b` is called and value is missing
        if next_equal == -1:
            log.error("No value after \"" + rest_str + "\". (Equal sign expected)")
            sys.exit(1)
        # find key:
        key = rest_str[0:next_equal]
        # go behind equal sign
        rest_str = rest_str[next_equal + 1:]
        # --- find value ---:
        # if value starts with quote (then go to next quote, ignore commas until
        # then)
        if rest_str[0] == '"':
            # next_quote ignores the first quote and looks for the next one
            next_quote = rest_str[1:].find('"')
            # next comma is then behind the quote
            next_comma = rest_str[1 + next_quote:].find(',')
            # if no other comma found, assume end of input
            if next_comma == -1:
                # if end reached and in quotes, ignore the leading and ending
                # quote for string
                value = rest_str[1:-1]
                rest_str = ""
            # take value until the next comma, rest_str starts then from behind
            # the comma (with the next key/value pair)
            else:
                # the value to set beginns with/after quote and goes to the
                # first comma after the next quote (e.g. it should skip the
                # quoted comma in "12 , 12")
                value = rest_str[1: next_quote + next_comma]
                # rest string should be after the next comma (outside/after the
                # next quote), and then go +2 to be first after the quote, and
                # second after the following comma
                rest_str = rest_str[next_quote + next_comma + 2:]
        # if value does not start with quote, just go to next comma
        else:
            # go to the next comma
            next_comma = rest_str.find(',')
            # if there is no next comma, assume end of input
            if next_comma == -1:
                value = rest_str
                rest_str = ""
            # if there is a comma, the value will end behind it and the rest_str
            # should follow with the next key/value pair
            else:
                value = rest_str[:next_comma]
                rest_str = rest_str[next_comma + 1:]
            # if the given values are int/float (and not in quotes), they
            # should be treated as such
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
        # add result
        results.append([key, value])
    # return key value pairs
    return results


# This class enables e.g. onyo set to receive a dictionary of key=value
class StoreDictKeyPair(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self._nargs = nargs
        super(StoreDictKeyPair, self).__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        my_dict = {}
        for pair in parse_key_values(values):
            k = pair[0]
            v = pair[1]
            my_dict[k] = v
        setattr(namespace, self.dest, my_dict)


# credit: https://stackoverflow.com/a/13429281
class SubcommandHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action):
        parts = super()._format_action(action)

        # strip the first line (metavar) of the subcommands section
        if action.nargs == argparse.PARSER:
            parts = parts.split("\n", 1)[1]

        return parts

    def _fill_text(self, text, width, indent):
        """
        This is a very, very naive approach to stripping rst syntax from
        docstrings. Sadly, docutils does not have a plain-text writer. That
        would be the ideal solution.
        """
        text = super()._fill_text(text, width, indent)

        # `` -> `
        text = text.replace('``', '`')
        # remove escapes of characters; everything is literal here
        text = text.replace('\\', '')

        return text
