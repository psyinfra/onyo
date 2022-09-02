#!/usr/bin/env python3
import logging

logging.basicConfig()
logger = logging.getLogger('onyo')


def shell_completion(args, onyo_root):
    """ Print a shell script for onyo shell completion.

    The output of this command should be "sourced" by bash or zsh to enable
    shell completion for onyo.

    Example:

        $ source <(onyo shell-completion)
        $ onyo --<PRESS TAB to display available option>
    """

    content = """\
#!bash
#
# This file is licensed under the ISC license.
# See the AUTHORS and LICENSE files for more information.
#
# bash/zsh completion support for onyo
#
# The output of this command is meant to be "sourced" by your shell in order to
# enable tab-completion for onyo.
#
# Instead of just running this command and seeing this output, run
#
#    source <(onyo shell-completion)
#

if [[ -n ${ZSH_VERSION-} ]]; then
    autoload -U +X bashcompinit && bashcompinit
fi

__ONYO='onyo'

# print top-level onyo commands
__onyo_list_commands() {
    local start='false'
    # COLUMNS=0 disables argparse's line wrapping
    COLUMNS=0 $__ONYO -h | \
    while IFS= read line; do
        [ "$line" == 'commands:' ] && start='true' && continue

        if [ "$start" == 'true' ]; then
            [ -z "$line" ] && break

            line=${line#${line%%[!\ ]*}} # trim leading spaces
            line=${line%% *} # trim everything after the command (help text)
            printf '%s\n' "$line"
        fi
    done
}


# print flags in long form (--) for onyo itself and all subcommands
__onyo_list_long_flags() {
    local cmd="$1"

    for i in 'onyo' $(__onyo_list_commands) ; do
        [ "$cmd" != "$i" ] && continue
        [ "$cmd" = 'onyo' ] && cmd=''

        local start='false'
        # COLUMNS=0 disables argparse's line wrapping
        COLUMNS=0 $__ONYO $cmd -h | \
        while IFS= read line; do
            [ "$line" = 'options:' ] && start='true' && continue

            if [ $start == 'true' ]; then
                [ -z "$line" ] && break

                line=${line#${line%%--*}} # trim anything before '--' (short arg and spaces)
                line=${line%% *} # trim everything after the argument (help text)

                printf '%s\n' "$line"
            fi
        done

        return 0
    done

    return 1
}


# print flags in short form (-) for onyo itself and all subcommands
__onyo_list_short_flags() {
    local cmd="$1"

    for i in 'onyo' $(__onyo_list_commands) ; do
        [ "$cmd" != "$i" ] && continue
        [ "$cmd" = 'onyo' ] && cmd=''

        local start='false'
        # COLUMNS=0 disables argparse's line wrapping
        COLUMNS=0 $__ONYO $cmd -h | \
        while IFS= read line; do
            [ "$line" = 'options:' ] && start='true' && continue

            if [ $start == 'true' ]; then
                [ -z "$line" ] && break

                line=${line#${line%%[!\ ]*}} # trim leading spaces
                line=${line%%, *} # trim everything after the short argument (long arg and help text)

                printf '%s\n' "$line"
            fi
        done

        return 0
    done

    return 1
}


__onyo_complete() {
    COMPREPLY=() # zero out response array
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"
    local cmd="${COMP_WORDS[1]}"

    [ "${prev##*/}" = 'onyo' ] && cmd='onyo'

    if [ "${cur:0:2}" = '--' ]; then
        COMPREPLY=($(compgen -W "$(__onyo_list_long_flags ${cmd})" -- "$cur"))
        return 0
    elif [ "${cur:0:1}" = '-' ]; then
        COMPREPLY=($(compgen -W "$(__onyo_list_short_flags ${cmd})" -- "$cur"))
        return 0
    fi

    # only bash >= 4 allows fall-through case statements, and macOS does not
    # ship a modern bash. Thus the global check for --help here.
    #
    # never suggest files or dirs after -h
    case "$prev" in
        -h|--help) return 1 ;;
    esac

    case "$cmd" in
        # no file or dir completion
        config|fsck)
            return 1
            ;;
        # TODO: git
        # suggest dirs only
        mkdir|tree)
            # TODO: append / and nospace
            COMPREPLY=($(compgen -d -o nospace -- "$cur" ))
            return 0
            ;;
        # suggest only one dir
        init|new)
            # TODO: limit to one dir
            COMPREPLY=($(compgen -d -- "$cur" ))
            return 1
            ;;
        # suggest onyo subcommands
        onyo)
            COMPREPLY=($(compgen -W "$(__onyo_list_commands)" -- "$cur"))
            return 0
            ;;
        # suggest files and dirs for all subcommands
        *)
            COMPREPLY=($(compgen -f -o plusdirs -- "$cur" ))
            return 0
            ;;
    esac
}

complete -F __onyo_complete onyo

#
# The output of this command is meant to be "sourced" by your shell in order to
# enable tab-completion for onyo.
#
# Instead of just running this command and seeing this output, run
#
#    source <(onyo shell-completion)
#
"""
    print(content)
