from __future__ import annotations

import os
import re
import sys
import textwrap
from argparse import ArgumentParser, PARSER, RawTextHelpFormatter
from pathlib import Path
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import rich

from onyo import cli
from onyo.lib.exceptions import (
    InvalidArgumentError,
    OnyoCLIExitCode,
    UIInputError,
)
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from argparse import Action
    from typing import (
        IO,
        List,
    )


class OnyoArgumentParser(ArgumentParser):
    r"""Rich-ified ArgumentParser.

    See Also
    --------
    argparse.ArgumentParser
    """

    def _print_message(self,
                       message: str,
                       file: IO[str] | None = None) -> None:
        r"""Print help text with Rich.
        """
        if message:
            rich.print(message, file=file)


class OnyoRawTextHelpFormatter(RawTextHelpFormatter):
    r"""Fix the sins of argparse's formatting; convert RST to Rich markup.

    See Also
    --------
    argparse.ArgumentParser.RawTextHelpFormatter
    """

    def _fill_text(self,
                   text: str,
                   width: int,
                   indent: str) -> str:
        r"""Wrap lines of text according to width.

        Just a wrapper to convert RST->Rich first.

        Parameters
        ----------
        text
            Text to wrap.
        width
            Max character of lines before wrapping.
        indent
            Indentation text to precede lines with.
        """
        text = rst_to_rich(text)
        return super()._fill_text(text, width, indent)

    def _format_action(self,
                       action: Action) -> str:
        r"""Build the full text for an Action (command, option, argument, etc).

        Just a wrapper to strip <COMMANDS> from subcommands section of help.

        Parameters
        ----------
        action
            ArgParse Action.
        """
        action_text = super()._format_action(action)
        # remove the superfluous first line (<COMMANDS>) of the subcommands section
        if action.nargs == PARSER:
            action_text = action_text.split("\n", 1)[1]

        return action_text

    def _format_action_invocation(self,
                                  action: Action) -> str:
        r"""Build the options/options+arguments/arguments string.

        Functionally identical to upstream, but with Rich markup added.

        Parameters
        ----------
        action
            ArgParse Action.
        """
        if action.option_strings:
            # -s, --long
            rendered_options = ', '.join([f"[cyan]{x}[/cyan]" for x in action.option_strings])

            if action.nargs != 0:
                # -s, --long ARGS
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                rendered_options += ' ' + f"[dark_cyan]{args_string}[/dark_cyan]"

            return rendered_options
        else:
            # ARGS
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return f"[dark_cyan]{metavar}[/dark_cyan]"

    def _split_lines(self,
                     text: str,
                     width: int) -> List[str]:
        r"""Wrap lines according to width.

        Just a wrapper to convert RST->Rich first.

        Parameters
        ----------
        text
            Text to wrap.
        width
            Max character length to wrap lines at.
        """
        text = rst_to_rich(text)
        return super()._split_lines(text, width)

    def start_section(self,
                      heading: str | None) -> None:
        r"""Start a section.

        Just a wrapper to stylize headings for Rich.

        Parameters
        ----------
        heading
            Heading text.
        """
        if heading:
            heading = f'[orange1]{heading.title()}[/orange1]'
        super().start_section(heading)


def rst_to_rich(text: str) -> str:
    r"""Convert RST to Rich syntax.

    Naively convert reStructuredText to Rich syntax, de-indent, and apply other
    cleanups to prepare text to print to the terminal.

    Parameters
    ----------
    text
        reStructuredText to convert.
    """
    # de-indent text
    text = textwrap.dedent(text).strip()

    # stylize arg descriptors (ALL CAPS ARGS)
    text = re.sub(r'\*\*([A-Z\-]+)\*\*', r'[dark_cyan]\1[/dark_cyan]', text)

    # stylize ** (bold)
    text = re.sub(r'\*\*([^*]+)\*\*', r'[bold]\1[/bold]', text)

    # stylize ``` (code blocks)
    text = re.sub('```\\n([^`]+)\\n```', r'\n[underline]\1[/underline]', text)
    # remove .. code:: statements
    # Onyo uses them for code that should be stylized in HTML but not help text.
    text = re.sub('.. code::[^\\n]+', '', text)

    # stylize `` (inline code markers) for flags
    text = re.sub('``(-[^`]+)``', r'[cyan]\1[/cyan]', text)

    # stylize remaining `` (inline code markers)
    text = re.sub('``([^`]+)``', r'[bold magenta]\1[/bold magenta]', text)

    # stylize headings
    text = re.sub('([^\\n]+)\\n---+\\n', r'[orange1]\1:[/orange1]\n', text)
    # and "rubric" as a hack because sphinx-argparse chokes on headings in
    # help/epilog text.
    text = re.sub('.. rubric:: ([^\\n]+)', r'[orange1]\1:[/orange1]', text)

    # make bullet points prettier
    text = text.replace(' * ', ' • ')

    # remove space-escaping for pluralizing arguments
    # (RST oddity that ``ASSET``s is illegal, but ``ASSET``\ s -> ASSETs)
    text = text.replace('\\ s', 's')

    return text


def build_parser(parser: ArgumentParser,
                 args: dict) -> None:
    r"""Add options or arguments to an ArgumentParser.

    Parameters
    ----------
    parser
        Parser to add arguments to.
    args
        Dictionary of option/argument dictionaries containing key-values to pass
        to ArgumentParser.add_argument(). The key name of the option/argument
        dictionary is passed as the value to ``dest``.

    See Also
    --------
    ArgumentParser.add_argument()

    Example
    -------
    An example option/argument dictionary::

        args = {
            'debug': dict(
                args=('-d', '--debug'),
                required=False,
                default=False,
                action='store_true',
                help=r"Enable debug logging."
            ),
        }
        build_parser(parser, args)
    """
    for cmd in args:
        args[cmd]['dest'] = cmd
        try:  # option flag
            parser.add_argument(
                *args[cmd]['args'],
                **{k: v for k, v in args[cmd].items() if k != 'args'})
        except KeyError:  # argument
            parser.add_argument(
                **{k: v for k, v in args[cmd].items()})


subcmds = None


def setup_parser() -> OnyoArgumentParser:
    r"""Setup and return a fully populated OnyoArgumentParser for Onyo and all subcommands.
    """
    from onyo.onyo_arguments import args_onyo
    from onyo.cli.cat import args_cat, epilog_cat
    from onyo.cli.config import args_config, epilog_config
    from onyo.cli.edit import args_edit, epilog_edit
    from onyo.cli.fsck import epilog_fsck
    from onyo.cli.get import args_get, epilog_get
    from onyo.cli.history import args_history, epilog_history
    from onyo.cli.init import args_init, epilog_init
    from onyo.cli.mkdir import args_mkdir, epilog_mkdir
    from onyo.cli.mv import args_mv, epilog_mv
    from onyo.cli.new import args_new, epilog_new
    from onyo.cli.rm import args_rm, epilog_rm
    from onyo.cli.set import args_set, epilog_set
    from onyo.cli.shell_completion import args_shell_completion, epilog_shell_completion
    from onyo.cli.tree import args_tree, epilog_tree
    from onyo.cli.unset import args_unset, epilog_unset

    global subcmds

    parser = OnyoArgumentParser(
        description='A text-based inventory system backed by git.',
        formatter_class=OnyoRawTextHelpFormatter
    )
    build_parser(parser, args_onyo)

    # subcommands
    subcmds = parser.add_subparsers(
        title='commands',
        dest='cmd'
    )
    subcmds.metavar = '<command>'
    #
    # subcommand "cat"
    #
    cmd_cat = subcmds.add_parser(
        'cat',
        description=cli.cat.__doc__,
        epilog=epilog_cat,
        formatter_class=parser.formatter_class,
        help='Print the contents of assets to the terminal.'
    )
    cmd_cat.set_defaults(run=cli.cat)
    build_parser(cmd_cat, args_cat)
    #
    # subcommand "config"
    #
    cmd_config = subcmds.add_parser(
        'config',
        description=cli.config.__doc__,
        epilog=epilog_config,
        formatter_class=parser.formatter_class,
        help='Set, query, and unset Onyo repository configuration options.'
    )
    cmd_config.set_defaults(run=cli.config)
    build_parser(cmd_config, args_config)
    #
    # subcommand "edit"
    #
    cmd_edit = subcmds.add_parser(
        'edit',
        description=cli.edit.__doc__,
        epilog=epilog_edit,
        formatter_class=parser.formatter_class,
        help='Open assets using an editor.'
    )
    cmd_edit.set_defaults(run=cli.edit)
    build_parser(cmd_edit, args_edit)
    #
    # subcommand "fsck"
    #
    cmd_fsck = subcmds.add_parser(
        'fsck',
        description=cli.fsck.__doc__,
        epilog=epilog_fsck,
        formatter_class=parser.formatter_class,
        help='Run a suite of integrity checks on the Onyo repository and its contents.'
    )
    cmd_fsck.set_defaults(run=cli.fsck)
    #
    # subcommand "get"
    #
    cmd_get = subcmds.add_parser(
        'get',
        description=cli.get.__doc__,
        epilog=epilog_get,
        formatter_class=parser.formatter_class,
        help='Return and sort asset values matching query patterns.'
    )
    cmd_get.set_defaults(run=cli.get)
    build_parser(cmd_get, args_get)
    #
    # subcommand "history"
    #
    cmd_history = subcmds.add_parser(
        'history',
        description=cli.history.__doc__,
        epilog=epilog_history,
        formatter_class=parser.formatter_class,
        help='Display the history of an asset or directory.'
    )
    cmd_history.set_defaults(run=cli.history)
    build_parser(cmd_history, args_history)
    #
    # subcommand "init"
    #
    cmd_init = subcmds.add_parser(
        'init',
        description=cli.init.__doc__,
        epilog=epilog_init,
        formatter_class=parser.formatter_class,
        help='Initialize a new Onyo repository.'
    )
    cmd_init.set_defaults(run=cli.init)
    build_parser(cmd_init, args_init)
    #
    # subcommand "mkdir"
    #
    cmd_mkdir = subcmds.add_parser(
        'mkdir',
        description=cli.mkdir.__doc__,
        epilog=epilog_mkdir,
        formatter_class=parser.formatter_class,
        help='Create directories.'
    )
    cmd_mkdir.set_defaults(run=cli.mkdir)
    build_parser(cmd_mkdir, args_mkdir)
    #
    # subcommand "mv"
    #
    cmd_mv = subcmds.add_parser(
        'mv',
        description=cli.mv.__doc__,
        epilog=epilog_mv,
        formatter_class=parser.formatter_class,
        help='Move assets or directories into a destination directory; or rename a directory.'
    )
    cmd_mv.set_defaults(run=cli.mv)
    build_parser(cmd_mv, args_mv)
    #
    # subcommand "new"
    #
    cmd_new = subcmds.add_parser(
        'new',
        description=cli.new.__doc__,
        epilog=epilog_new,
        formatter_class=parser.formatter_class,
        help='Create new assets and populate with key-value pairs.'
    )
    cmd_new.set_defaults(run=cli.new)
    build_parser(cmd_new, args_new)
    #
    # subcommand "rm"
    #
    cmd_rm = subcmds.add_parser(
        'rm',
        description=cli.rm.__doc__,
        epilog=epilog_rm,
        formatter_class=parser.formatter_class,
        help='Delete assets and directories.'
    )
    cmd_rm.set_defaults(run=cli.rm)
    build_parser(cmd_rm, args_rm)
    #
    # subcommand "set"
    #
    cmd_set = subcmds.add_parser(
        'set',
        description=cli.set.__doc__,
        epilog=epilog_set,
        formatter_class=parser.formatter_class,
        help='Set the value of keys for assets.'
    )
    cmd_set.set_defaults(run=cli.set)
    build_parser(cmd_set, args_set)
    #
    # subcommand "shell-completion"
    #
    cmd_shell_completion = subcmds.add_parser(
        'shell-completion',
        description=cli.shell_completion.__doc__,
        epilog=epilog_shell_completion,
        formatter_class=parser.formatter_class,
        help='Display a tab-completion script for Onyo.'
    )
    cmd_shell_completion.set_defaults(run=cli.shell_completion)
    build_parser(cmd_shell_completion, args_shell_completion)
    #
    # subcommand "tree"
    #
    cmd_tree = subcmds.add_parser(
        'tree',
        description=cli.tree.__doc__,
        epilog=epilog_tree,
        formatter_class=parser.formatter_class,
        help='List the assets and directories of a directory in ``tree`` format.'
    )
    cmd_tree.set_defaults(run=cli.tree)
    build_parser(cmd_tree, args_tree)
    #
    # subcommand "unset"
    #
    cmd_unset = subcmds.add_parser(
        'unset',
        description=cli.unset.__doc__,
        epilog=epilog_unset,
        formatter_class=parser.formatter_class,
        help='Remove keys from assets.'
    )
    cmd_unset.set_defaults(run=cli.unset)
    build_parser(cmd_unset, args_unset)

    return parser


def get_subcmd_index(arglist: list,
                     start: int = 1) -> int | None:
    r"""Get the index of the Onyo subcommand in a list of arguments.

    Parameters
    ----------
    arglist
        The list of command line arguments passed to a Python script. Usually
        ``sys.argv``.
    start
        The index to start searching from.

    Example
    -------
    >>> subcmd_index = get_subcmd_index(sys.argv)
    """
    onyo_flags_with_args = ['-C', '--onyopath']

    try:
        # find the first non-flag argument
        nonflag = next((a for a in arglist[start:] if a[0] != '-'))
        index = arglist.index(nonflag, start)
    except (StopIteration, ValueError):
        return None

    # check if it's the subcommand, or just an argument to a flag
    if arglist[index - 1] in onyo_flags_with_args:
        index = get_subcmd_index(arglist, index + 1)

    return index


def main() -> None:
    r"""Execute Onyo's CLI.
    """
    #
    # ARGPARSE Hack #1
    #
    # This unfortunately-located-hack passes uninterpreted args to "onyo config".
    # nargs=argparse.REMAINDER is supposed to do this, but did not work for our
    # needs, and as of Python 3.8 is soft-deprecated (due to being buggy).
    # See https://bugs.python.org/issue17050#msg315716 ; https://bugs.python.org/issue9334
    passthrough_subcmds = ['config']
    subcmd_index = get_subcmd_index(sys.argv)
    if subcmd_index and sys.argv[subcmd_index] in passthrough_subcmds:
        # display the onyo subcmd's --help, and don't pass it through
        if not any(x in sys.argv for x in ['-h', '--help']):
            sys.argv.insert(subcmd_index + 1, '--')

    #
    # ARGPARSE Hack #2
    #
    # This hack makes argparse print the help text for the subcommand when an
    # unknown argument is encountered. Previously it only printed help for the
    # top-level command.
    # See https://bugs.python.org/issue34479
    global subcmds
    # parse the arguments
    parser = setup_parser()
    args, extras = parser.parse_known_args()
    if extras:
        if args.cmd:
            subcmds._name_parser_map[args.cmd].print_usage(file=sys.stderr)
        parser.error("unrecognized arguments: %s" % " ".join(extras))

    #
    # Begin normal, non-hack `main` stuff
    #
    # configure user interface
    ui.set_debug(args.debug)
    ui.set_yes(args.yes)
    ui.set_quiet(args.quiet)

    # run the subcommand
    if subcmd_index:
        old_cwd = Path.cwd()
        os.chdir(args.opdir)
        # normally exit 1 on error. `get` is a special case. Exit with 2 on
        # error to mimic `grep`'s behavior.
        cmd_error_codes = {
            'cat': 2,
            'get': 2,
        }
        error_returncode = cmd_error_codes.get(args.cmd, 1)

        try:
            args.run(args)
        except InvalidArgumentError as e:
            # special treatment for this error b/c it's meant to capture
            # malformed calls, that aren't covered by argparse itself.
            # Same style of reporting as any other argparse error:
            subcmds._name_parser_map[args.cmd].print_usage(file=sys.stderr)
            parser.error(str(e))
        except CalledProcessError as e:
            # CalledProcessError itself is not informative to the user.
            # As far as there was something useful in that process' stdout/stderr
            # we usually let it through. If not, it should result in a dedicated exception,
            # that we can treat here accordingly.
            ui.log_debug(str(e))
            sys.exit(e.returncode)
        except OnyoCLIExitCode as e:
            ui.log_debug(ui.format_traceback(e))
            sys.exit(e.returncode)
        except UIInputError as e:
            ui.error(e)
            ui.error("Use the --yes switch for non-interactive mode.")
        except Exception as e:
            # TODO: This may need to be nicer, but in any case: Turn any exception/error into a message and exit
            #       non-zero here, in order to have this generic last catcher.
            ui.error(e)
            code = e.returncode if hasattr(e, 'returncode') else error_returncode  # pyre-ignore
            sys.exit(code)
        except KeyboardInterrupt:
            ui.error("User interrupted.")
            sys.exit(1)
        finally:
            os.chdir(old_cwd)
        if ui.error_count > 0:
            # We may have reported errors while being able to proceed (hence no exception bubbled up).
            # That's fine, but still exit non-zero.
            sys.exit(error_returncode)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
