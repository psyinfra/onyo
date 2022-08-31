#!/usr/bin/env python3

from onyo import commands

import logging
import argparse
import sys
import os

logging.basicConfig()
logger = logging.getLogger('onyo')
logger.setLevel(logging.INFO)


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


def parse_args():
    parser = argparse.ArgumentParser(
        description='A text-based inventory system backed by git.',
        formatter_class=SubcommandHelpFormatter
    )
    parser.add_argument(
        '-C',
        '--onyopath',
        required=False,
        default=os.getcwd(),
        help='run as if onyo was started in <path>'
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
    subcommands = parser.add_subparsers(
        title="commands"
    )
    subcommands.metavar = '<command>'
    #
    # subcommand cat
    #
    cmd_cat = subcommands.add_parser(
        'cat',
        help='print the contents of an asset'
    )
    cmd_cat.set_defaults(run=commands.cat)
    cmd_cat.add_argument(
        'file',
        metavar='file',
        nargs='+',
        help='asset(s) to print'
    )
    #
    # subcommand "config"
    #
    cmd_config = subcommands.add_parser(
        'config',
        help='set onyo options in the repository'
    )
    cmd_config.set_defaults(run=commands.config)
    cmd_config.add_argument(
        'command',
        metavar='command',
        nargs=argparse.REMAINDER,
        help='configuration key to set in .onyo/config'
    )
    #
    # subcommand "edit"
    #
    cmd_edit = subcommands.add_parser(
        'edit',
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
        'file',
        metavar='file',
        nargs='+',
        help='filename of asset(s) to edit'
    )
    #
    # subcommand "fsck"
    #
    cmd_fsck = subcommands.add_parser(
        'fsck',
        help='check the onyo repository for sanity, and run YAML and onyo validation on all assets'
    )
    cmd_fsck.set_defaults(run=commands.fsck)
    #
    # subcommand "git"
    #
    cmd_git = subcommands.add_parser(
        'git',
        help='run git commands in the onyo repository'
    )
    cmd_git.set_defaults(run=commands.git)
    cmd_git.add_argument(
        '-C', '--directory',
        metavar='directory',
        help='directory to run git in'
    )
    cmd_git.add_argument(
        'command',
        metavar='<command>',
        nargs=argparse.REMAINDER,
        help='git command to run'
    )
    #
    # subcommand "history"
    #
    cmd_history = subcommands.add_parser(
        'history',
        help='show the history of an asset or directory'
    )
    cmd_history.set_defaults(run=commands.history)
    cmd_history.add_argument(
        'source',
        metavar='source',
        nargs='?',
        help='asset or directory to show the history of'
    )
    cmd_history.add_argument(
        '-I', '--non-interactive',
        required=False,
        default=False,
        action='store_true',
        help='print the git log instead of opening an interactive tig session'
    )
    #
    # subcommand "init"
    #
    cmd_init = subcommands.add_parser(
        'init',
        help='initialize an onyo repository'
    )
    cmd_init.set_defaults(run=commands.init)
    cmd_init.add_argument(
        'directory',
        metavar='directory',
        nargs='?',
        help='initialize <directory> as an onyo repository'
    )
    #
    # subcommand "mkdir"
    #
    cmd_mkdir = subcommands.add_parser(
        'mkdir',
        help='create a directory (and anchor for git)'
    )
    cmd_mkdir.set_defaults(run=commands.mkdir)
    cmd_mkdir.add_argument(
        'directory',
        metavar='directory',
        nargs='+',
        help='directory to create'
    )
    #
    # subcommand "mv"
    #
    cmd_mv = subcommands.add_parser(
        'mv',
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
        metavar='source',
        nargs='+',
        help='source ...'
    )
    cmd_mv.add_argument(
        'destination',
        metavar='destination',
        help='destination'
    )
    #
    # subcommand "new"
    #
    cmd_new = subcommands.add_parser(
        'new',
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
        required=False,
        default='',
        help='the template to use to seed a new asset'
    )
    cmd_new.add_argument(
        'directory',
        metavar='directory',
        help='add a new asset to <directory>'
    )
    #
    # subcommand "set"
    #
    cmd_set = subcommands.add_parser(
        'set',
        help='set values in assets'
    )
    cmd_set.set_defaults(run=commands.set)
    cmd_set.add_argument(
        '-d', '--depth',
        metavar='depth',
        type=int,
        required=False,
        default=-1,
        help='descend at most "n" levels of directories below the starting-point; used only with --recursive'
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
        metavar="keys",
        help='key-value pairs to set in asset files; multiple pairs can be separated by commas (e.g. key=value,key2=value2)'
    )
    cmd_set.add_argument(
        'source',
        metavar='source',
        default='.',
        nargs='*',
        help='assets/directories for which to set values'
    )
    #
    # subcommand "tree"
    #
    cmd_tree = subcommands.add_parser(
        'tree',
        help='print the contents of a directory in a tree-like format'
    )
    cmd_tree.set_defaults(run=commands.tree)
    cmd_tree.add_argument(
        'directory',
        metavar='directory',
        nargs='*',
        help='directories to print'
    )
    #
    # subcommand "rm"
    #
    cmd_rm = subcommands.add_parser(
        'rm',
        help='delete asset(s)'
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
        'source',
        metavar='source',
        nargs='+',
        help='asset(s) to delete'
    )
    return parser


def main():
    parser = parse_args()
    args = parser.parse_args()

    if args.onyopath:
        onyo_root = args.onyopath

    # TODO: Do onyo fsck here, test if onyo_root exists, .onyo exists, is git repo, other checks

    if args.debug:
        logger.setLevel(logging.DEBUG)
    if len(sys.argv) > 1 and not args.debug:
        args.run(args, onyo_root)
    elif len(sys.argv) > 2:
        args.run(args, onyo_root)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
