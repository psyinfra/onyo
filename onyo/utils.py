import subprocess
import logging
import os
import sys
import shlex
import glob
import yaml
import argparse
from ruamel.yaml import YAML
from onyo import commands
from git import Repo, exc
import textwrap

logging.basicConfig()
logger = logging.getLogger('onyo')


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
        logger.error(run_error)
        sys.exit(1)
    else:
        logger.debug(cmd + " " + comment)
    return run_output


# checks if a given path is git-directory (needs to be main-level)
def is_git_dir(directory):
    try:
        Repo(directory).git_dir
        return True
    except exc.InvalidGitRepositoryError:
        return False


def get_git_root(path):
    # first checks if file is in git from current position
    try:
        git_repo = Repo(path, search_parent_directories=True)
        git_root = git_repo.git.rev_parse("--show-toplevel")
        if os.path.isdir(os.path.join(git_root, ".onyo")):
            return git_root
    except (exc.NoSuchPathError, exc.InvalidGitRepositoryError):
        logger.error(path + " is no onyo repository.")
        sys.exit(1)
        return git_root


def get_full_filepath(git_directory, file):
    full_filepath = os.path.join(git_directory, file)
    if not os.path.exists(full_filepath):
        full_filepath = os.path.join(git_directory, os.getcwd())
        full_filepath = os.path.join(full_filepath, file)
    if not os.path.exists(full_filepath):
        logger.error(file + " not found.")
        sys.exit(1)
    return full_filepath


def get_editor():
    editor = os.environ.get('EDITOR')
    if not editor:
        logger.info("$EDITOR is not set.")
    elif editor and run_cmd("which " + editor).rstrip("\n") == "":
        logger.warning(editor + " could not be found.")
    else:
        return editor
    # try using vi/nano as editor
    if run_cmd("which nano").rstrip("\n") != "":
        logger.info("nano is used as editor.")
        editor = 'nano'
    elif run_cmd("which vi").rstrip("\n") != "":
        logger.info("vi is used as editor.")
        editor = 'vi'
    # if no editor is set, and nano/vi both are not found.
    else:
        logger.error("No editor found.")
        sys.exit(1)
    return editor


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
    if not os.path.isfile(file):
        logger.error(file + " does not exist.")
        sys.exit(1)
    # create and edit a temporary file, and if that is valid replace original
    temp_file = os.path.join(get_git_root(onyo_root), os.path.join(".onyo/temp/", os.path.basename(file)))
    if not os.path.isfile(temp_file):
        run_cmd("cp \"" + file + "\" \"" + temp_file + "\"")
    # When temp-file exists, ask if to use it
    elif os.path.isfile(temp_file):
        while True:
            edit_temp = str(input("Temporary changes for " + file + " exist. Continue editing? (y/N) "))
            if edit_temp in ['y', 'Y', 'yes']:
                break
            elif edit_temp == 'n':
                run_cmd("cp \"" + file + "\" \"" + temp_file + "\"")
                break
    further_editing = 'y'
    while further_editing == 'y':
        # do actual editing:
        os.system(get_editor() + " \"" + temp_file + "\"")
        # check syntax
        with open(temp_file, "r") as stream:
            try:
                yaml.safe_load(stream)
                problem_str = validate_file(temp_file, file, onyo_root)
                if problem_str == "":
                    run_cmd("mv \"" + temp_file + "\" \"" + file + "\"")
                else:
                    # TODO: better exception needed
                    raise yaml.YAMLError("\nOnyo Validation failed for:\n" + problem_str)
                return
            except yaml.YAMLError as e:
                while True:
                    further_editing = str(input(str(e) + "Continue editing? (y/N) "))
                    if further_editing in ['y', 'Y', 'yes']:
                        break
                    elif further_editing == 'n':
                        output_str = "No changes made."
                        # onyo new should neither create a new file nor a
                        # temp-file, and have a special info message
                        if (onyo_new):
                            run_cmd("rm \"" + file + "\"")
                            output_str = "No new asset \"" + os.path.relpath(file, onyo_root) + "\" created."
                        run_cmd("rm \"" + temp_file + "\"")
                        logger.info(output_str)
                        sys.exit(1)
    return


def build_git_add_cmd(directory, file):
    return "git -C \"" + directory + "\" add \"" + file + "\""


def get_list_of_assets(repo_path):
    assets = []
    for elem in glob.iglob(repo_path + '**/**', recursive=True):
        if os.path.isfile(elem):
            # when assets are in .gitignore, they should not be listed as such
            if run_cmd("git -C \"" + repo_path + "\" check-ignore --no-index \"" + elem + "\""):
                continue
            assets.append([os.path.relpath(elem, repo_path), os.path.basename(elem)])
    return assets


def prepare_directory(directory):
    if os.path.isdir(os.path.join(os.getcwd(), directory)):
        location = os.path.join(os.getcwd(), directory)
    else:
        logger.error(directory + " does not exist.")
        sys.exit(1)
    return location


def parse_args():
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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='print the contents of an asset'
    )
    cmd_cat.set_defaults(run=commands.cat)
    cmd_cat.add_argument(
        'asset',
        metavar='ASSET',
        nargs='+',
        help='asset(s) to print'
    )
    #
    # subcommand "config"
    #
    cmd_config = subcmds.add_parser(
        'config',
        description=textwrap.dedent(commands.config.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='set onyo options in the repository'
    )
    cmd_config.set_defaults(run=commands.config)
    cmd_config.add_argument(
        'key',
        metavar='KEY',
        nargs=argparse.REMAINDER,
        help='configuration key to set in .onyo/config'
    )
    #
    # subcommand "edit"
    #
    cmd_edit = subcmds.add_parser(
        'edit',
        description=textwrap.dedent(commands.edit.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='edit an asset'
    )
    cmd_edit.set_defaults(run=commands.edit)
    cmd_edit.add_argument(
        '-I', '--non-interactive',
        required=False,
        default=False,
        action='store_true',
        help='do not prompt or open the editor'
    )
    cmd_edit.add_argument(
        'asset',
        metavar='ASSET',
        nargs='+',
        help='asset(s) to edit'
    )
    #
    # subcommand "fsck"
    #
    cmd_fsck = subcmds.add_parser(
        'fsck',
        description=textwrap.dedent(commands.fsck.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='check the onyo repository for sanity, and run YAML and onyo validation on all assets'
    )
    cmd_fsck.set_defaults(run=commands.fsck)
    #
    # subcommand "git"
    #
    cmd_git = subcmds.add_parser(
        'git',
        description=textwrap.dedent(commands.git.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='run git commands in the onyo repository'
    )
    cmd_git.set_defaults(run=commands.git)
    cmd_git.add_argument(
        'command',
        metavar='<command>',
        nargs=argparse.REMAINDER,
        help='git command to run'
    )
    #
    # subcommand "history"
    #
    cmd_history = subcmds.add_parser(
        'history',
        description=textwrap.dedent(commands.history.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='show the history of an asset or directory'
    )
    cmd_history.set_defaults(run=commands.history)
    cmd_history.add_argument(
        '-I', '--non-interactive',
        required=False,
        default=False,
        action='store_true',
        help='print the git log instead of opening an interactive tig session'
    )
    cmd_history.add_argument(
        'path',
        metavar='PATH',
        nargs='?',
        help='asset or directory to show the history of'
    )
    #
    # subcommand "init"
    #
    cmd_init = subcmds.add_parser(
        'init',
        description=textwrap.dedent(commands.init.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='initialize an onyo repository'
    )
    cmd_init.set_defaults(run=commands.init)
    cmd_init.add_argument(
        'directory',
        metavar='DIR',
        nargs='?',
        help='initialize DIR as an onyo repository'
    )
    #
    # subcommand "mkdir"
    #
    cmd_mkdir = subcmds.add_parser(
        'mkdir',
        description=textwrap.dedent(commands.mkdir.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='create a directory (with git anchor)'
    )
    cmd_mkdir.set_defaults(run=commands.mkdir)
    cmd_mkdir.add_argument(
        'directory',
        metavar='DIR',
        nargs='+',
        help='directory to create'
    )
    #
    # subcommand "mv"
    #
    cmd_mv = subcmds.add_parser(
        'mv',
        description=textwrap.dedent(commands.mv.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='move an asset'
    )
    cmd_mv.set_defaults(run=commands.mv)
    cmd_mv.add_argument(
        '-f', '--force',
        required=False,
        default=False,
        action='store_true',
        help='overwrite the target if it already exists; never prompt'
    )
    cmd_mv.add_argument(
        '-r', '--rename',
        required=False,
        default=False,
        action='store_true',
        help='allow an asset to be renamed (i.e. modify the pseudo keys)'
    )
    cmd_mv.add_argument(
        'source',
        metavar='SOURCE',
        nargs='+',
        help='source ...'
    )
    cmd_mv.add_argument(
        'destination',
        metavar='DEST',
        help='destination'
    )
    #
    # subcommand "new"
    #
    cmd_new = subcmds.add_parser(
        'new',
        description=textwrap.dedent(commands.new.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='create a new asset'
    )
    cmd_new.set_defaults(run=commands.new)
    cmd_new.add_argument(
        '-I', '--non-interactive',
        required=False,
        default=False,
        action='store_true',
        help='do not prompt or open the editor; values must be piped in (e.g. echo "<type>\\n<make>\\n<model>\\n<serial>" | onyo new -I shelf/)'
    )
    cmd_new.add_argument(
        '-t', '--template',
        metavar='TEMPLATE',
        required=False,
        default='',
        help='the template to use to seed a new asset'
    )
    cmd_new.add_argument(
        'directory',
        metavar='DIR',
        help='add a new asset to DIR'
    )
    #
    # subcommand "set"
    #
    cmd_set = subcmds.add_parser(
        'set',
        description=textwrap.dedent(commands.set.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
        help='assets or directories for which to set values'
    )
    #
    # subcommand shell-completion
    #
    cmd_shell_completion = subcmds.add_parser(
        'shell-completion',
        description=textwrap.dedent(commands.shell_completion.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='a shell completion for onyo, suitable for use with "source"'
    )
    cmd_shell_completion.set_defaults(run=commands.shell_completion)
    #
    # subcommand "tree"
    #
    cmd_tree = subcmds.add_parser(
        'tree',
        description=textwrap.dedent(commands.tree.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='print the contents of a directory in a tree-like format'
    )
    cmd_tree.set_defaults(run=commands.tree)
    cmd_tree.add_argument(
        'directory',
        metavar='DIR',
        nargs='*',
        help='directories to print'
    )
    #
    # subcommand "rm"
    #
    cmd_rm = subcmds.add_parser(
        'rm',
        description=textwrap.dedent(commands.rm.__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        help='delete asset(s) and directories'
    )
    cmd_rm.set_defaults(run=commands.rm)
    cmd_rm.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='silence output (requires the --yes flag)'
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
        help='assets or directories to delete'
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
            logger.error("No value after \"" + rest_str + "\". (Equal sign expected)")
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


# Custom help formatter to strip the first line (metavar) for subcommands from
# help output.
# credit: https://stackoverflow.com/a/13429281
class SubcommandHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action):
        parts = super(argparse.RawDescriptionHelpFormatter, self)._format_action(action)
        if action.nargs == argparse.PARSER:
            parts = "\n".join(parts.split("\n")[1:])
        return parts
