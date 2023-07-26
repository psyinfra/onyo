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
    from onyo.shared_arguments import (
        shared_arg_depth,
        shared_arg_dry_run,
        shared_arg_filter,
        shared_arg_message,
        shared_arg_quiet,
        shared_arg_yes
    )

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
    from onyo.commands.cat import arg_asset
    cmd_cat = subcmds.add_parser(
        'cat',
        description=textwrap.dedent(commands.cat.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.cat.__doc__)
    )
    cmd_cat.set_defaults(run=commands.cat)
    cmd_cat.add_argument(**arg_asset)
    #
    # subcommand "config"
    #
    from onyo.commands.config import arg_git_config_args
    cmd_config = subcmds.add_parser(
        'config',
        description=textwrap.dedent(commands.config.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.config.__doc__)
    )
    cmd_config.set_defaults(run=commands.config)
    cmd_config.add_argument(**arg_git_config_args)
    #
    # subcommand "edit"
    #
    from onyo.commands.edit import arg_asset
    cmd_edit = subcmds.add_parser(
        'edit',
        description=textwrap.dedent(commands.edit.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.edit.__doc__)
    )
    cmd_edit.set_defaults(run=commands.edit)
    cmd_edit.add_argument(*(shared_arg_message['args']),
                          **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_edit.add_argument(*(shared_arg_quiet['args']),
                          **{k: v for k, v in shared_arg_quiet.items() if k != 'args'})
    cmd_edit.add_argument(*(shared_arg_yes['args']),
                          **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    cmd_edit.add_argument(**arg_asset)
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
    from onyo.commands.get import (
        arg_machine_readable,
        arg_keys,
        arg_path,
        arg_sort_ascending,
        arg_sort_descending
    )
    cmd_get = subcmds.add_parser(
        'get',
        description=textwrap.dedent(commands.get.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.get.__doc__)
    )
    cmd_get.set_defaults(run=commands.get)
    cmd_get.add_argument(*(shared_arg_depth['args']),
                         **{k: v for k, v in shared_arg_depth.items() if k != 'args'})
    cmd_get.add_argument(*(shared_arg_filter['args']),
                         **{k: v for k, v in shared_arg_filter.items() if k != 'args'})
    cmd_get.add_argument(*arg_machine_readable['args'],
                         **{k: v for k, v in arg_machine_readable.items() if k != 'args'})
    cmd_get.add_argument(*arg_keys['args'],
                         **{k: v for k, v in arg_keys.items() if k != 'args'})
    cmd_get.add_argument(*arg_path['args'],
                         **{k: v for k, v in arg_path.items() if k != 'args'})
    cmd_get.add_argument(*arg_sort_ascending['args'],
                         **{k: v for k, v in arg_sort_ascending.items() if k != 'args'})
    cmd_get.add_argument(*arg_sort_descending['args'],
                         **{k: v for k, v in arg_sort_descending.items() if k != 'args'})
    #
    # subcommand "history"
    #
    from onyo.commands.history import arg_interactive, arg_path
    cmd_history = subcmds.add_parser(
        'history',
        description=textwrap.dedent(commands.history.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.history.__doc__)
    )
    cmd_history.set_defaults(run=commands.history)
    cmd_history.add_argument(*(arg_interactive['args']),
                             **{k: v for k, v in arg_interactive.items() if k != 'args'})
    cmd_history.add_argument(**arg_path)
    #
    # subcommand "init"
    #
    from onyo.commands.init import arg_directory
    cmd_init = subcmds.add_parser(
        'init',
        description=textwrap.dedent(commands.init.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.init.__doc__)
    )
    cmd_init.set_defaults(run=commands.init)
    cmd_init.add_argument(**arg_directory)
    #
    # subcommand "mkdir"
    #
    from onyo.commands.mkdir import arg_directory
    cmd_mkdir = subcmds.add_parser(
        'mkdir',
        description=textwrap.dedent(commands.mkdir.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.mkdir.__doc__)
    )
    cmd_mkdir.set_defaults(run=commands.mkdir)
    cmd_mkdir.add_argument(*(shared_arg_message['args']),
                           **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_mkdir.add_argument(*(shared_arg_quiet['args']),
                           **{k: v for k, v in shared_arg_quiet.items() if k != 'args'})
    cmd_mkdir.add_argument(*(shared_arg_yes['args']),
                           **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    cmd_mkdir.add_argument(**arg_directory)
    #
    # subcommand "mv"
    #
    from onyo.commands.mv import arg_source, arg_destination
    cmd_mv = subcmds.add_parser(
        'mv',
        description=textwrap.dedent(commands.mv.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.mv.__doc__)
    )
    cmd_mv.set_defaults(run=commands.mv)
    cmd_mv.add_argument(*(shared_arg_message['args']),
                        **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_mv.add_argument(*(shared_arg_quiet['args']),
                        **{k: v for k, v in shared_arg_quiet.items() if k != 'args'})
    cmd_mv.add_argument(*(shared_arg_yes['args']),
                        **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    cmd_mv.add_argument(**arg_source)
    cmd_mv.add_argument(**arg_destination)
    #
    # subcommand "new"
    #
    from onyo.commands.new import arg_template, arg_edit, arg_keys, arg_path, arg_tsv
    cmd_new = subcmds.add_parser(
        'new',
        description=textwrap.dedent(commands.new.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.new.__doc__)
    )
    cmd_new.set_defaults(run=commands.new)
    cmd_new.add_argument(*(shared_arg_message['args']),
                         **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_new.add_argument(*(arg_template['args']),
                         **{k: v for k, v in arg_template.items() if k != 'args'})
    cmd_new.add_argument(*(arg_edit['args']),
                         **{k: v for k, v in arg_edit.items() if k != 'args'})
    cmd_new.add_argument(*(arg_keys['args']),
                         **{k: v for k, v in arg_keys.items() if k != 'args'}, action=StoreKeyValuePairs)
    cmd_new.add_argument(*arg_path['args'],
                         **{k: v for k, v in arg_path.items() if k != 'args'})
    cmd_new.add_argument(*(arg_tsv['args']),
                         **{k: v for k, v in arg_tsv.items() if k != 'args'})
    cmd_new.add_argument(*(shared_arg_yes['args']),
                         **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    #
    # subcommand "rm"
    #
    from onyo.commands.rm import arg_path
    cmd_rm = subcmds.add_parser(
        'rm',
        description=textwrap.dedent(commands.rm.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.rm.__doc__)
    )
    cmd_rm.set_defaults(run=commands.rm)
    cmd_rm.add_argument(*(shared_arg_message['args']),
                        **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_rm.add_argument(*(shared_arg_quiet['args']),
                        **{k: v for k, v in shared_arg_quiet.items() if k != 'args'})
    cmd_rm.add_argument(*(shared_arg_yes['args']),
                        **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    cmd_rm.add_argument(**arg_path)
    #
    # subcommand "set"
    #
    from onyo.commands.set import arg_rename, arg_keys, arg_path
    cmd_set = subcmds.add_parser(
        'set',
        description=textwrap.dedent(commands.set.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.set.__doc__)
    )
    cmd_set.set_defaults(run=commands.set)
    cmd_set.add_argument(*(shared_arg_depth['args']),
                         **{k: v for k, v in shared_arg_depth.items() if k != 'args'})
    cmd_set.add_argument(*(shared_arg_filter['args']),
                         **{k: v for k, v in shared_arg_filter.items() if k != 'args'})
    cmd_set.add_argument(*(shared_arg_message['args']),
                         **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_set.add_argument(*(shared_arg_dry_run['args']),
                         **{k: v for k, v in shared_arg_dry_run.items() if k != 'args'})
    cmd_set.add_argument(*(shared_arg_quiet['args']),
                         **{k: v for k, v in shared_arg_quiet.items() if k != 'args'})
    cmd_set.add_argument(*(arg_rename['args']),
                         **{k: v for k, v in arg_rename.items() if k != 'args'})
    cmd_set.add_argument(*(shared_arg_yes['args']),
                         **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    cmd_set.add_argument(*(arg_keys['args']),
                         **{k: v for k, v in arg_keys.items() if k != 'args'},
                         action=StoreKeyValuePairs)
    cmd_set.add_argument(*(arg_path['args']),
                         **{k: v for k, v in arg_path.items() if k != 'args'})
    #
    # subcommand "shell-completion"
    #
    from onyo.commands.shell_completion import arg_shell
    cmd_shell_completion = subcmds.add_parser(
        'shell-completion',
        description=textwrap.dedent(commands.shell_completion.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.shell_completion.__doc__)
    )
    cmd_shell_completion.set_defaults(run=commands.shell_completion,
                                      parser=parser)
    cmd_shell_completion.add_argument(*(arg_shell['args']),
                                      **{k: v for k, v in arg_shell.items() if k != 'args'})
    #
    # subcommand "tree"
    #
    from onyo.commands.tree import arg_directory
    cmd_tree = subcmds.add_parser(
        'tree',
        description=textwrap.dedent(commands.tree.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.tree.__doc__)
    )
    cmd_tree.set_defaults(run=commands.tree)
    cmd_tree.add_argument(**arg_directory)
    #
    # subcommand "unset"
    #
    from onyo.commands.unset import arg_keys, arg_path
    cmd_unset = subcmds.add_parser(
        'unset',
        description=textwrap.dedent(commands.unset.__doc__),
        formatter_class=SubcommandHelpFormatter,
        help=textwrap.dedent(commands.unset.__doc__)
    )
    cmd_unset.set_defaults(run=commands.unset)
    cmd_unset.add_argument(*(shared_arg_depth['args']),
                           **{k: v for k, v in shared_arg_depth.items() if k != 'args'})
    cmd_unset.add_argument(*(shared_arg_filter['args']),
                           **{k: v for k, v in shared_arg_filter.items() if k != 'args'})
    cmd_unset.add_argument(*(shared_arg_message['args']),
                           **{k: v for k, v in shared_arg_message.items() if k != 'args'})
    cmd_unset.add_argument(*(shared_arg_dry_run['args']),
                           **{k: v for k, v in shared_arg_dry_run.items() if k != 'args'})
    cmd_unset.add_argument(*(shared_arg_quiet['args']),
                           **{k: v for k, v in shared_arg_quiet.items() if k != 'args'})
    cmd_unset.add_argument(*(shared_arg_yes['args']),
                           **{k: v for k, v in shared_arg_yes.items() if k != 'args'})
    cmd_unset.add_argument(*(arg_keys['args']),
                           **{k: v for k, v in arg_keys.items() if k != 'args'})
    cmd_unset.add_argument(*(arg_path['args']),
                           **{k: v for k, v in arg_path.items() if k != 'args'})

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
