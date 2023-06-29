import argparse
import logging
import os
import sys
import textwrap

from onyo import commands
from onyo._version import __version__
from pathlib import Path
from typing import Optional, Sequence, Union

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')
log.setLevel(logging.INFO)


class StoreKeyValuePairs(argparse.Action):
    def __init__(self, option_strings: Sequence[str], dest: str,
                 nargs: Union[None, int, str] = None, **kwargs) -> None:
        self._nargs = nargs
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace, key_values: list[str],
                 option_string: Optional[str] = None) -> None:
        results = {}
        for pair in key_values:
            k, v = pair.split('=', maxsplit=1)
            try:
                v = int(v)
            except ValueError:
                try:
                    float(v)
                except ValueError:
                    pass
            results[k] = v
        setattr(namespace, self.dest, results)


# credit: https://stackoverflow.com/a/13429281
class SubcommandHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action: argparse.Action) -> str:
        parts = super()._format_action(action)

        # strip the first line (metavar) of the subcommands section
        if action.nargs == argparse.PARSER:
            parts = parts.split("\n", 1)[1]

        return parts

    def _fill_text(self, text: str, width: int, indent: str) -> str:
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


def parse_key_values(string):
    """
    Convert a string of key-value pairs to a dictionary.

    The shell interprets the key-value string before it is passed to argparse.
    As a result, no quotes are passed through, but the chunking follows what the
    quoting declared.

    Because of the lack of quoting, this function cannot handle a comma in
    either the key or value.
    """
    results = {k: v for k, v in (pair.split('=') for pair in string.split(','))}
    for k, v in results.items():
        try:
            results.update({k: int(v)})
        except ValueError:
            try:
                results.update({k: float(v)})
            except ValueError:
                pass

    return results


def directory(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def file(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def git_config(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def path(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def template(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='A text-based inventory system backed by git.',
        formatter_class=SubcommandHelpFormatter
    )
    parser.add_argument(
        '-C',
        '--onyopath',
        dest='opdir',
        metavar='DIR',
        required=False,
        default=Path.cwd(),
        type=directory,
        help='Run Onyo commands from inside of DIR'
    )
    parser.add_argument(
        '-d',
        '--debug',
        required=False,
        default=False,
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s {version}'.format(version=__version__),
        help="Print onyo's version and exit"
    )
    # subcommands
    subcmds = parser.add_subparsers(
        title='commands'
    )
    subcmds.metavar = '<command>'
    #
    # subcommand "cat"
    #
    cmd_cat = subcmds.add_parser(
        'cat',
        description=textwrap.dedent(commands.cat.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.cat.__doc__)
    )
    cmd_cat.set_defaults(run=commands.cat)
    cmd_cat.add_argument(
        'asset',
        metavar='ASSET',
        nargs='+',
        type=file,
        help='List paths of asset(s) to print'
    )
    #
    # subcommand "config"
    #
    cmd_config = subcmds.add_parser(
        'config',
        description=textwrap.dedent(commands.config.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.config.__doc__)
    )
    cmd_config.set_defaults(run=commands.config)
    cmd_config.add_argument(
        'git_config_args',
        metavar='ARGS',
        nargs='+',
        type=git_config,
        help='Arguments configure the options in .onyo/config'
    )
    #
    # subcommand "edit"
    #
    cmd_edit = subcmds.add_parser(
        'edit',
        description=textwrap.dedent(commands.edit.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.edit.__doc__)
    )
    cmd_edit.set_defaults(run=commands.edit)
    cmd_edit.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_edit.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Silence messages printed to stdout. Does not suppress interactive '
            'editors. Requires the --yes flag')
    )
    cmd_edit.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Respond "yes" to any prompts. The --yes flag is required to '
            'use --quiet')
    )
    cmd_edit.add_argument(
        'asset',
        metavar='ASSET',
        nargs='+',
        type=file,
        help='List paths of asset(s) to edit'
    )
    #
    # subcommand "fsck"
    #
    cmd_fsck = subcmds.add_parser(
        'fsck',
        description=textwrap.dedent(commands.fsck.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.fsck.__doc__)
    )
    cmd_fsck.set_defaults(run=commands.fsck)
    #
    # subcommand "get"
    #
    cmd_get = subcmds.add_parser(
        'get',
        description=textwrap.dedent(commands.get.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.get.__doc__)
    )
    cmd_get.set_defaults(run=commands.get)
    cmd_get.add_argument(
        '-d', '--depth',
        metavar='DEPTH',
        type=int,
        required=False,
        default=0,
        help=(
            'Descent up to DEPTH levels into directories specified. DEPTH=0 '
            'descends recursively without limit')
    )
    cmd_get.add_argument(
        '-f', '--filter',
        metavar='FILTER',
        nargs='+',
        type=str,
        default=None,
        help=(
            'Add a filter to only show assets matching KEY=VALUE. Multiple '
            'filters, regular expressions, and pseudo-keys can be used.')
    )
    cmd_get.add_argument(
        '-H', '--machine-readable',
        dest='machine_readable',
        action='store_true',
        help=(
            'Display asset(s) separated by new lines, and keys by tabs instead '
            'of printing a formatted table')
    )
    cmd_get.add_argument(
        '-k', '--keys',
        metavar='KEYS',
        nargs='+',
        help=(
            'Key value(s) to return. Pseudo-keys (information not stored in '
            'the asset file, e.g. filename) are also available for queries')
    )
    cmd_get.add_argument(
        '-p', '--path',
        metavar='PATH',
        type=path,
        nargs='+',
        help='List asset(s) or directory(s) to search through'
    )
    cmd_get.add_argument(
        '-s', '--sort-ascending',
        dest='sort_ascending',
        action='store_true',
        default=False,
        help='Sort output in ascending order (excludes --sort-descending)'
    )
    cmd_get.add_argument(
        '-S', '--sort-descending',
        dest='sort_descending',
        action='store_true',
        default=False,
        help='Sort output in descending order (excludes --sort-ascending)'
    )
    #
    # subcommand "history"
    #
    cmd_history = subcmds.add_parser(
        'history',
        description=textwrap.dedent(commands.history.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.history.__doc__)
    )
    cmd_history.set_defaults(run=commands.history)
    cmd_history.add_argument(
        '-I', '--non-interactive',
        dest='interactive',
        required=False,
        default=True,
        action='store_false',
        help=(
            "Use the interactive history tool (specified in '.onyo/config' "
            "under 'onyo.history.interactive') to display the history of the "
            "repository, an asset or a directory")
    )
    cmd_history.add_argument(
        'path',
        metavar='PATH',
        nargs='?',
        type=path,
        help='Specify an asset or a directory to show the history of'
    )
    #
    # subcommand "init"
    #
    cmd_init = subcmds.add_parser(
        'init',
        description=textwrap.dedent(commands.init.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.init.__doc__)
    )
    cmd_init.set_defaults(run=commands.init)
    cmd_init.add_argument(
        'directory',
        metavar='DIR',
        nargs='?',
        type=directory,
        help='Initialize DIR as an onyo repository'
    )
    #
    # subcommand "mkdir"
    #
    cmd_mkdir = subcmds.add_parser(
        'mkdir',
        description=textwrap.dedent(commands.mkdir.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.mkdir.__doc__)
    )
    cmd_mkdir.set_defaults(run=commands.mkdir)
    cmd_mkdir.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_mkdir.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='Silence messages printed to stdout. Requires the --yes flag'
    )
    cmd_mkdir.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Respond "yes" to any prompts. The --yes flag is required to '
            'use --quiet')
    )
    cmd_mkdir.add_argument(
        'directory',
        metavar='DIR',
        nargs='+',
        type=directory,
        help='List directory(s) to create'
    )
    #
    # subcommand "mv"
    #
    cmd_mv = subcmds.add_parser(
        'mv',
        description=textwrap.dedent(commands.mv.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.mv.__doc__)
    )
    cmd_mv.set_defaults(run=commands.mv)
    cmd_mv.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_mv.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='Silence messages to stdout. Requires the --yes flag'
    )
    cmd_mv.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='Respond "yes" to any prompts. Is required to use --yes flag'
    )
    cmd_mv.add_argument(
        'source',
        metavar='SOURCE',
        nargs='+',
        type=path,
        help='List asset(s) and/or directory(s) to move into DEST'
    )
    cmd_mv.add_argument(
        'destination',
        metavar='DEST',
        type=path,
        help='Destination to move SOURCE(s) into'
    )
    #
    # subcommand "new"
    #
    cmd_new = subcmds.add_parser(
        'new',
        description=textwrap.dedent(commands.new.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.new.__doc__)
    )
    cmd_new.set_defaults(run=commands.new)
    cmd_new.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_new.add_argument(
        '-t', '--template',
        metavar='TEMPLATE',
        required=False,
        type=template,
        help='Specify the template to seed the new asset(s)'
    )
    cmd_new.add_argument(
        '-e', '--edit',
        required=False,
        default=False,
        action='store_true',
        help='Open new assets to edit them before creation'
    )
    cmd_new.add_argument(
        '-k', '--keys',
        required=False,
        action=StoreKeyValuePairs,
        metavar="KEYS",
        nargs='+',
        help=(
            'Set key-value pairs in the new asset(s). Multiple pairs can be '
            'specified (e.g. key=value key2=value2)')
    )
    cmd_new.add_argument(
        '-p', '--path',
        metavar='ASSET',
        type=path,
        nargs='*',
        help=(
            'Specify the directory and name of the new asset(s) '
            '(in the format DIR/ASSET). Excludes usage of --tsv')
    )
    cmd_new.add_argument(
        '-tsv', '--tsv',
        metavar='TSV',
        required=False,
        type=path,
        help=(
            'Read information of new assets from a tsv file describing them. '
            'Excludes the usage of --path')
    )
    cmd_new.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='Respond "yes" to any prompts. Is required to use --yes flag'
    )
    #
    # subcommand "rm"
    #
    cmd_rm = subcmds.add_parser(
        'rm',
        description=textwrap.dedent(commands.rm.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.rm.__doc__)
    )
    cmd_rm.set_defaults(run=commands.rm)
    cmd_rm.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_rm.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='Silence messages to stdout. Requires the --yes flag'
    )
    cmd_rm.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='Respond "yes" to any prompts. Is required for usage of --quiet'
    )
    cmd_rm.add_argument(
        'path',
        metavar='PATH',
        nargs='+',
        type=path,
        help='List asset(s) and/or directory(s) to delete'
    )
    #
    # subcommand "set"
    #
    cmd_set = subcmds.add_parser(
        'set',
        description=textwrap.dedent(commands.set.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.set.__doc__)
    )
    cmd_set.set_defaults(run=commands.set)
    cmd_set.add_argument(
        '-d', '--depth',
        metavar='DEPTH',
        type=int,
        required=False,
        default=0,
        help=(
            'Descent up to DEPTH levels into directories specified. DEPTH=0 '
            'descends recursively without limit')
    )
    cmd_set.add_argument(
        '-f', '--filter',
        metavar='FILTER',
        nargs='+',
        type=str,
        default=None,
        help=(
            'Add a filter to only show assets matching KEY=VALUE. Multiple '
            'filters, regular expressions, and pseudo-keys can be used.')
    )
    cmd_set.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_set.add_argument(
        '-n', '--dry-run',
        required=False,
        default=False,
        action='store_true',
        help='Perform a non-interactive trial-run without making any changes'
    )
    cmd_set.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='Silence messages printed to stdout. Requires the --yes flag'
    )
    cmd_set.add_argument(
        '-r', '--rename',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Permit assigning values to pseudo-keys that would result in the '
            'file(s) being renamed.')
    )
    cmd_set.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='Respond "yes" to any prompts. Is required to use --yes flag'
    )
    cmd_set.add_argument(
        '-k', '--keys',
        required=True,
        action=StoreKeyValuePairs,
        metavar="KEYS",
        nargs='+',
        help=(
            'Specify key-value pairs to set in asset(s). Multiple pairs can '
            'be specified (e.g. key=value key2=value2)')
    )
    cmd_set.add_argument(
        '-p', '--path',
        metavar='PATH',
        nargs='*',
        type=path,
        help='List asset(s) and/or directorie(s) to set KEY=VALUE in'
    )
    #
    # subcommand "shell-completion"
    #
    cmd_shell_completion = subcmds.add_parser(
        'shell-completion',
        description=textwrap.dedent(commands.shell_completion.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.shell_completion.__doc__)
    )
    cmd_shell_completion.set_defaults(run=commands.shell_completion,
                                      parser=parser)
    cmd_shell_completion.add_argument(
        '-s', '--shell',
        metavar='SHELL',
        required=False,
        default='zsh',
        choices=['zsh'],
        help='Specify the shell for which to generate tab completion for'
    )
    #
    # subcommand "tree"
    #
    cmd_tree = subcmds.add_parser(
        'tree',
        description=textwrap.dedent(commands.tree.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.tree.__doc__)
    )
    cmd_tree.set_defaults(run=commands.tree)
    cmd_tree.add_argument(
        'directory',
        metavar='DIR',
        nargs='*',
        type=directory,
        help='List directory(s) to print tree of'
    )
    #
    # subcommand "unset"
    #
    cmd_unset = subcmds.add_parser(
        'unset',
        description=textwrap.dedent(commands.unset.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.unset.__doc__)
    )
    cmd_unset.set_defaults(run=commands.unset)
    cmd_unset.add_argument(
        '-d', '--depth',
        metavar='DEPTH',
        type=int,
        required=False,
        default=0,
        help=(
            'Descent up to DEPTH levels into directories specified. DEPTH=0 '
            'descends recursively without limit')
    )
    cmd_unset.add_argument(
        '-f', '--filter',
        metavar='FILTER',
        nargs='+',
        type=str,
        default=None,
        help=(
            'Add a filter to only show assets matching KEY=VALUE. Multiple '
            'filters, regular expressions, and pseudo-keys can be used.')
    )
    cmd_unset.add_argument(
        '-m', '--message',
        metavar='MESSAGE',
        nargs=1,
        action='append',
        type=str,
        help=(
            'Use the given MESSAGE as the commit message (rather than the '
            'default). If multiple -m options are given, their values are '
            'concatenated as separate paragraphs')
    )
    cmd_unset.add_argument(
        '-n', '--dry-run',
        required=False,
        default=False,
        action='store_true',
        help=(
            'Perform a non-interactive trial-run without making any changes '
            'on assets')

    )
    cmd_unset.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='Silence messages printed to stdout. Requires the --yes flag'
    )
    cmd_unset.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='Respond "yes" to any prompts. Is required to use --yes flag'
    )
    cmd_unset.add_argument(
        '-k', '--keys',
        required=True,
        metavar="KEYS",
        nargs='+',
        type=str,
        help=(
            'Specify keys to unset in assets. Multiple keys can be given '
            '(e.g. key key2 key3)')
    )
    cmd_unset.add_argument(
        '-p', '--path',
        metavar="PATH",
        nargs='*',
        type=path,
        help='List asset(s) and/or directory(s) for which to unset values in'
    )

    return parser


def get_subcmd_index(arglist, start: int = 1) -> Union[int, None]:
    """
    Get the index of the subcommand from a provided list of arguments (usually sys.argv).

    Returns the index on success, and None in failure.
    """
    # TODO: alternatively, this could use TabCompletion._argparse_to_dict()
    # flags which accept an argument
    flagplus = ['-C', '--onyopath']

    try:
        # find the first non-flag argument
        nonflag = next((a for a in arglist[start:] if a[0] != '-'))
        index = arglist.index(nonflag, start)
    except (StopIteration, ValueError):
        return None

    # check if it's the subcommand, or just an argument to a flag
    if arglist[index - 1] in flagplus:
        index = get_subcmd_index(arglist, index + 1)

    return index


def main() -> None:
    # NOTE: this unfortunately-located-hack is to pass uninterpreted args to
    # "onyo config".
    # nargs=argparse.REMAINDER is supposed to do this, but did not work for our
    # needs, and as of Python 3.8 is soft-deprecated (due to being buggy).
    # For more information, see https://docs.python.org/3.10/library/argparse.html#arguments-containing
    passthrough_subcmds = ['config']
    subcmd_index = get_subcmd_index(sys.argv)
    if subcmd_index and sys.argv[subcmd_index] in passthrough_subcmds:
        # display the subcmd's --help, and don't pass it through
        if not any(x in sys.argv for x in ['-h', '--help']):
            sys.argv.insert(subcmd_index + 1, '--')

    # parse the arguments
    parser = setup_parser()
    args = parser.parse_args()

    # debugging
    if args.debug:
        log.setLevel(logging.DEBUG)

    # run the subcommand
    if subcmd_index:
        old_cwd = Path.cwd()
        os.chdir(args.opdir)
        try:
            args.run(args)
        except Exception as e:
            # TODO: This may need to be nicer, but in any case: Turn any exception/error into a message and exit
            #       non-zero here, in order to have this generic last catcher.
            log.error(str(e))
            sys.exit(1)
        finally:
            os.chdir(old_cwd)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
