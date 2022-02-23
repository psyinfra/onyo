#!/usr/bin/env python3

from onyo import commands

import logging
import argparse
import sys
import os

logging.basicConfig()
logger = logging.getLogger('onyo')
logger.setLevel(logging.WARNING)

def parse_args():
    parser = argparse.ArgumentParser(
        description='A text-based inventory system backed by git.'
    )

    # if ONYO_REPOSITORY_DIR as environmental variable is set, uses it as
    # default onyo dir, otherwise it uses the current working directory as
    # default, but this can always be overwritten by terminal.
    onyo_default_repo = os.environ.get('ONYO_REPOSITORY_DIR')
    if onyo_default_repo == None:
        onyo_default_repo = os.getcwd()

    # subcommands
    subcommands = parser.add_subparsers(
        title="onyo commands",
        description="Entry points for onyo"
    )
    # subcommand "init"
    cmd_init = subcommands.add_parser(
        'init',
        help='Initialize a onyo repository'
    )
    cmd_init.set_defaults(run=commands.init)
    cmd_init.add_argument(
        'directory',
        metavar='directory',
        nargs='?',
        default=onyo_default_repo,
        help='Directory to initialize onyo repository'
    )
    # subcommand "mv"
    cmd_mv = subcommands.add_parser(
        'mv',
        help='Move an asset in onyo'
    )
    cmd_mv.set_defaults(run=commands.mv)
    cmd_mv.add_argument(
        '-f', '--force',
        required=False,
        default=False,
        action='store_true',
        help='Forcing to move file'
    )
    cmd_mv.add_argument(
        '-r', '--rename',
        required=False,
        default=False,
        action='store_true',
        help='Rename file'
    )
    cmd_mv.add_argument(
        'source',
        metavar='source',
        nargs='+',
        help='Source file'
    )
    cmd_mv.add_argument(
        'destination',
        metavar='destination',
        help='Destination file'
    )
    # subcommand "new"
    cmd_new = subcommands.add_parser(
        'new',
        help='Create a new onyo asset'
    )
    cmd_new.set_defaults(run=commands.new)
    cmd_new.add_argument(
        'location',
        metavar='location',
        help='Directory to add the new onyo asset'
    )
    # subcommand "edit"
    cmd_edit = subcommands.add_parser(
        'edit',
        help='Edit an existing onyo asset'
    )
    cmd_edit.set_defaults(run=commands.edit)
    cmd_edit.add_argument(
        'file',
        metavar='file',
        help='Filename of asset to edit'
    )
    # subcommand "tree"
    cmd_tree = subcommands.add_parser(
        'tree',
        help='Show tree of folder'
    )
    cmd_tree.set_defaults(run=commands.tree)
    cmd_tree.add_argument(
        'directory',
        metavar='directory',
        nargs='?',
        default=onyo_default_repo,
        help='Directory to show tree'
    )
    return parser


def main():
    parser = parse_args()
    args = parser.parse_args()

    if len(sys.argv) > 1:
        args.run(args)
    else:
        parser.print_help()



if __name__ == '__main__':
    main()
