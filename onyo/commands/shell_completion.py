#!/usr/bin/env python3

import argparse
from onyo.utils import setup_parser


class TabCompletion:
    """
    A superclass for tab-completion classes. It accepts an ArgumentParser
    object, and returns a completion script via the `completion_script`
    property.

    Subclasses must implement the _completion() method to return the full
    completion script.

    Parameters
    ----------
    parser : ArgumentParser
        The populated ArgumentParser object to generate tab completion for.
    type_to_action_map : dict, optional
        A dictionary map of types to shell actions. Shells often have default
        actions (such as "_files" in ZSH). Alternatively, a function can be
        called.

        Example:
            type_to_action_map = {
                'directory': '_path_files -/',
                'file': '_files',
                'path': '_files',
                'template': '_path_files -W $(_template_dir) -g "*(.)"'
            }
    epilogue : string, optional
        A string to include at the end of the shell completion script. This is
        useful when including a custom function to be invoked as an action for a
        custom type (see type_to_action_map).

        Example:
            epilogue = '_template_dir() { printf "/a/template/directory" }'

    Properties
    ----------
    completion_script
        Returns the completion script.
    """
    def __init__(self, parser, *, type_to_action_map={}, epilogue=''):
        self._cmd_tree = self._argparse_to_dict(parser)
        self._type_to_action_map = type_to_action_map
        self._completion_script = None
        self._epilogue = epilogue

    @property
    def completion_script(self):
        if not self._completion_script:
            self._completion_script = self._completion(self._cmd_tree)

        return self._completion_script

    def _argparse_to_dict(self, parser):
        """Convert an ArgumentParser object to a dict-tree.
        ArgumentParser was clearly not intended to allow the information
        registered in it to be queried by anything other than itself. Extracting
        information is possible, just awkward.

        This function returns a dict-tree, that is intended to be consistent and
        thus easier to traverse.

        NOTE: This function uses private ArgumentParser variables and functions.
              They may change without notice.

        Example output:
        {
          "flags": {
            "-I,--igloo": {
              "help": "not terribly helpful"
              "required": false,
            },
          },
          "subcmds": {
            "mv": {
              "help": "not terribly helpful",
              "flags": {
                "-I,--igloo": {
                  "help": "not terribly helpful",
                  "required": false,
                  "args": {
                    "shape": {
                      "nargs": *,
                      "type": 'directory',
                      "choices": []
                    }
                  }
                },
                { ...}
              }
              "args": {
                "shape": {
                  "nargs": 1,
                  "choices": ['circle', 'square']
            },
            {...}
          }
        }
        """
        cmd_tree = {
            'args': {},
            'flags': {},
            'subcmds': {}
        }

        for sp in parser._actions:
            if isinstance(sp, argparse._SubParsersAction):  # a group of subcommands
                # _name_parser_map is the only place that the subcommand objects are
                # available. BUT, it does not contain the help text.

                # loop over _name_parser_map to operate on the child flags
                for subcmd, subcmd_parser in sp._name_parser_map.items():
                    cmd_tree['subcmds'][subcmd] = self._argparse_to_dict(subcmd_parser)

                # loop over _choices_actions to extract the help text
                for ca in sp._choices_actions:
                    cmd_tree['subcmds'][ca.metavar]['help'] = ca.help.replace("'", "'\\''")
            elif sp.option_strings:  # option flag
                flag_string = ','.join(sp.option_strings)
                cmd_tree['flags'][flag_string] = {
                    "help": sp.help.replace("'", "'\\''"),
                    "required": sp.required
                }

                # arguments for a flag
                cmd_tree['flags'][flag_string]['args'] = {}

                # TODO: handle non-int nargs
                # TODO: handle >1 nargs
                if sp.nargs is None or sp.nargs > 0:
                    cmd_tree['flags'][flag_string]['args'][sp.metavar] = self._build_arg_dict(sp)
            else:  # argument
                cmd_tree['args'][sp.metavar] = self._build_arg_dict(sp)

        return cmd_tree

    def _build_arg_dict(self, sp):
        """
        Return a dict populated with all the fields for an argument.
        """
        arg = {
            "choices": sp.choices,
            "help": sp.help.replace("'", "'\\''"),
            "nargs": self._get_nargs(sp),
            "required": self._get_arg_required(sp),
            "type": self._get_type(sp)
        }
        return arg

    def _get_arg_required(self, sp):
        """
        Return whether an argument is required.
        """
        # ? means 0 or 1 arguments
        # * means 0 or more arguments
        # + means 1 or more arguments
        # N means N arguments
        if sp.nargs in ['?', '*']:
            return False
        else:
            return True

    def _get_nargs(self, sp):
        """Return an nargs string.
        This returns the nargs string in nargs format. The problem is that
        argparse often does not require that nargs is set, and assumes a value
        (1) for the unset field.

        See Python's argparse docs for more information:
        https://docs.python.org/3/library/argparse.html#nargs
        """
        if sp.nargs is None:
            return 1

        return sp.nargs

    def _get_type(self, sp):
        """
        Return the name of an argument's type.
        """
        if sp.type is None:
            return None
        else:
            try:
                return sp.type.__name__
            except AttributeError:
                # an instance of an object
                return sp.type.__class__.__name__


class Zsh(TabCompletion):
    def _completion(self, cmd_tree):
        return self._zsh_completion(cmd_tree)

    def _zsh_completion(self, cmd_tree):
        """
        Return a script for ZSH tab completion, suitable for use with the
        "source" command.
        """
        # This does not attempt to implement the full spec for _arguments or optspec.
        # It should, however, cover a significant enough portion as to be useful.
        toplevel_flags = self._zsh_build_args_and_flags(cmd_tree)
        subcommands = self._zsh_build_subcommands(cmd_tree)
        subcommands_case_statement = self._zsh_build_subcommands_case_statement(cmd_tree)

        content = f"""\
#compdef onyo

#
# ZSH completion script for Onyo
#

_onyo() {{
  local curcontext="$curcontext" ret=1
  local -a state state_descr line
  local -A opt_args

  # $words is modified as it is passed down through the script. This keeps an
  # unmodified copy of the expanded command.
  local -a fullwords
  fullwords=("${{words[@]}}")

  local -a args subcommands
  args=( )
  toplevel_flags=( {toplevel_flags} )

  subcommands=( {subcommands} )

  _arguments -C $args \
                $toplevel_flags \
                ':subcommand:->subcommand' \
                '*::options:->options' && ret=0

  case $state in
      subcommand)
          _describe -t subcommands 'onyo subcommand' subcommands && ret=0
      ;;

      options)
          curcontext="${{curcontext%:*}}-$words[2]:"

          case $words[1] in
              {subcommands_case_statement}

              *) args+=( '*: :_default' ) ;;
          esac

          _arguments -s -S $args && ret=0
    ;;
  esac

  {self._epilogue}

  return ret
}}

# NOTE: If installing the output of this script in your fpath,
#       uncomment '_onyo "$@"' and comment-out "compdef _onyo onyo".
#_onyo "$@"
compdef _onyo onyo

#
# ZSH completion script for Onyo
#
# To use this script and enable tab completion for Onyo rather than just seeing
# this output, run
#
#    source <(onyo shell-completion)
#
"""
        return content

    def _zsh_build_args_and_flags(self, cmd_tree, padding=0):
        """
        Return a string (for use in a ZSH list) containing rules for flags (with
        their arguments) and standalone arguments.
        Format information can be found in _zsh_build_arg() and _zsh_build_flag().
        """
        output = ''

        for flag, flag_tree in cmd_tree['flags'].items():
            output += (' ' * padding) + self._zsh_build_flag(flag, flag_tree) + '\n'

        for arg, arg_tree in cmd_tree['args'].items():
            output += (' ' * padding) + "'" + self._zsh_build_arg(arg, arg_tree) + "'\n"

        return output

    def _zsh_build_arg(self, arg, arg_tree):
        """
        Build and return a string containing the ZSH completion rule for an
        argument.

        NOTE: As per the spec, standalone arguments are one per line, whereas
        arguments to a flag are concatenated on a single line.

        NOTE: Omitted support:
        - :::
        """
        output = ''

        # can an unbound number of arguments can be accepted.
        if arg_tree['nargs'] in ['*', '+']:  # '*' >= 0 ; '+' >= 1
            output += '*'

        # required vs optional
        if arg_tree['required']:
            output += ':'
        else:
            output += '::'

        if arg_tree['choices']:  # a list of choices
            output += "{}:({})".format(arg, ' '.join(arg_tree['choices']))
        else:
            try:
                output += "{}:{}".format(arg, self._type_to_action_map[arg_tree['type']])
            except KeyError:  # no specified action for this type
                # A single unquoted space indicates that an argument is required,
                # but that it is not possible to suggest matches for it.
                output += "{}:{}".format(arg, ' ')

        return output

    def _zsh_build_flag(self, flag, flag_tree):
        """
        Build and return a string containing the ZSH completion rule for a flag
        and its arguments.

        NOTE: Omitted support:
        - Exclusion
        """
        output = ''
        chunks = {
            "exclude": '',
            "flag": '',
            "help": '',
            "action": ''
        }

        #
        # build exclude
        #
        # e.g.: '(- : *)'{{-h,--help}}'[display usage information]'
        # TODO

        # always exclude for -h/--help
        if flag == '-h,--help':
            chunks['exclude'] = "(- : *)"

        #
        # build flag
        #
        if ',' in flag:  # multiple (i.e. short and long form)
            chunks['flag'] = "{" + flag + "}"
        else:  # one
            chunks['flag'] = flag

        #
        # build help
        #
        chunks['help'] = "[" + flag_tree['help'] + "]"

        #
        # build arg/actions
        #
        for arg, arg_tree in flag_tree['args'].items():
            chunks['action'] += self._zsh_build_arg(arg, arg_tree)

        # ZSH's _argument optspec format covers:
        #   - exclusion (pattern which should disallow matching)
        #   - the flag/arg itself
        #   - help text
        #   - arguments to the flag
        #   - a list of choices (or an action that will return a list) for arg completion
        # This is in the format:
        #     '(-e --exclude)--flag[help text]:arg:_files'
        # However, when there are short and long forms, it is idiomatic to use shell
        # expansion. Note the location of the single quotes:
        #     '(-e --exclude)'{-f,--flag}'[help text]:arg:_files
        # This makes it a bit more awkward to format the output than one would
        # normally assume.
        # The format is explained in more detail here:
        #     https://zsh.sourceforge.io/Doc/Release/Completion-System.html#Completion-Functions
        if ',' in chunks['flag']:  # multiple flags (i.e. short and long form)
            if chunks['exclude']:
                # '(-e --exclude)'{-f,--flag}'[help text]:arg:_files
                output = "'" + chunks['exclude'] + "'" + chunks['flag'] + "'" + chunks['help'] + chunks['action'] + "'"
            else:
                # {-f,--flag}'[help text]:arg:_files'
                output = chunks['flag'] + "'" + chunks['help'] + chunks['action'] + "'"
        else:  # one flag
            # '(-e --exclude)--flag[help text]:arg:_files'
            output = "'" + chunks['exclude'] + chunks['flag'] + chunks['help'] + chunks['action'] + "'"

        return output

    def _zsh_build_subcommands(self, cmd_tree):
        """
        Return a string (for use in a ZSH list) containing subcommands and their
        help text in the format of:
            'subcommand1:help text'
            'subcommand2:help text'
            '...'
        """
        subcmd_list = ["'{}:{}'".format(subcmd, subcmd_tree['help'])
                       for subcmd, subcmd_tree in cmd_tree['subcmds'].items()]

        return "\n".join(subcmd_list)

    def _zsh_build_subcommands_case_statement(self, cmd_tree):
        """
        Return a ZSH case statement for subcommands. Within each is defined the
        flags and args for the appropriate command.

        This case statement is entered through the use of an action state
        (i.e. ->string) of an option. Specifically '*::options:->options'
        """
        case = ''

        for subcmd, subcmd_tree in cmd_tree['subcmds'].items():
            case += f"{subcmd})\n"
            case += '    args+=(\n'

            case += self._zsh_build_args_and_flags(subcmd_tree, padding=8)

            case += "    )\n"
            case += "    ;;\n"

        return case


def shell_completion(args, onyo_root):
    """
    Display a shell script for tab completion for Onyo.

    The output of this command should be "sourced" to enable tab completion.

    example:

        $ source <(onyo shell-completion)
        $ onyo --<PRESS TAB to display available options>
    """
    parser = setup_parser()

    if args.shell == 'zsh':
        type_to_action_map = {
            'git_config': '_git-config',
            'directory': '_path_files -W $(_onyo_dir) -/',
            'file': '_files -W $(_onyo_dir)',
            'path': '_files -W $(_onyo_dir)',
            'template': '_path_files -W $(_template_dir) -g "*(.)"'
        }
        epilogue = """
        # load _git, so that _git-config is available for onyo config completion
        whence -v _git-config > /dev/null || _git

        _onyo_dir() {
          local REPO=$PWD

          # check if -C or --onyopath is used
          for i in {1..$#fullwords}; do
            if [ "$fullwords[$i]" = "-C" ] || [ "$fullwords[$i]" = "--onyopath" ] ; then
              REPO=$fullwords[$i+1]
              break
            fi
          done

          printf "$REPO"
        }

        _template_dir() {
          DIR=$(_onyo_dir)

          while [ "$DIR" != '/' ]; do
            TEMPLATE_DIR="${DIR}/.onyo/templates"
            if [ -d "$TEMPLATE_DIR" ] ; then
              printf "$TEMPLATE_DIR"
              return
            else
              DIR=$(dirname "$DIR")
            fi
          done
        }
        """
        tc = Zsh(parser,
                 type_to_action_map=type_to_action_map,
                 epilogue=epilogue)
        content = tc.completion_script
    else:
        content = ''

    # TODO: add bash

    print(content)
