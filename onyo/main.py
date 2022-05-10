#!/usr/bin/env python3

from onyo import commands

import logging
import argparse
import sys
import os

logging.basicConfig()
logger = logging.getLogger('onyo')
logger.setLevel(logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(
        description='A text-based inventory system backed by git.'
    )
    parser.add_argument(
        '-d',
        '--debug',
        required=False,
        default=False,
        action='store_true',
        help='Enable debug logging'
    )

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
        help='Enable renaming of asset file'
    )
    cmd_mv.add_argument(
        'source',
        metavar='source',
        nargs='+',
        help='Source ...'
    )
    cmd_mv.add_argument(
        'destination',
        metavar='destination',
        help='Destination'
    )
    # subcommand "new"
    cmd_new = subcommands.add_parser(
        'new',
        help='Create a new onyo asset'
    )
    cmd_new.set_defaults(run=commands.new)
    cmd_new.add_argument(
        '-I', '--non-interactive',
        required=False,
        default=False,
        action='store_true',
        help='Creates the new asset without opening editor'
    )
    cmd_new.add_argument(
        'directory',
        metavar='directory',
        help='Directory to add the new onyo asset'
    )
    # subcommand "edit"
    cmd_edit = subcommands.add_parser(
        'edit',
        help='Edit an existing onyo asset'
    )
    cmd_edit.set_defaults(run=commands.edit)
    cmd_edit.add_argument(
        '-I', '--non-interactive',
        required=False,
        default=False,
        action='store_true',
        help='Suppress opening the editor'
    )
    cmd_edit.add_argument(
        'file',
        metavar='file',
        nargs='+',
        help='Filename of asset to edit'
    )
    # subcommand cat
    cmd_cat = subcommands.add_parser(
        'cat',
        help='Show contents of file'
    )
    cmd_cat.set_defaults(run=commands.cat)
    cmd_cat.add_argument(
        'file',
        metavar='file',
        nargs='+',
        help='File to show content'
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
        nargs='*',
        help='Directories to show tree'
    )
    # subcommand "git"
    cmd_git = subcommands.add_parser(
        'git',
        help='Run git command in onyo'
    )
    cmd_git.set_defaults(run=commands.git)
    cmd_git.add_argument(
        '-C', '--directory',
        metavar='directory',
        help='Command to run in onyo'
    )
    cmd_git.add_argument(
        'command',
        metavar='command',
        nargs=argparse.REMAINDER,
        help='Command to run in onyo'
    )
    # subcommand "mkdir"
    cmd_mkdir = subcommands.add_parser(
        'mkdir',
        help='Create folder(s) in onyo'
    )
    cmd_mkdir.set_defaults(run=commands.mkdir)
    cmd_mkdir.add_argument(
        'directory',
        metavar='directory',
        nargs='+',
        help='Directory to create in onyo'
    )
    # subcommand "rm"
    cmd_rm = subcommands.add_parser(
        'rm',
        help='Delete assets from onyo'
    )
    cmd_rm.set_defaults(run=commands.rm)
    cmd_rm.add_argument(
        '-q', '--quiet',
        required=False,
        default=False,
        action='store_true',
        help='Silence output (requires the --yes flag)'
    )
    cmd_rm.add_argument(
        '-y', '--yes',
        required=False,
        default=False,
        action='store_true',
        help='Respond "yes" to the prompt'
    )
    cmd_rm.add_argument(
        'source',
        metavar='source',
        nargs='+',
        help='Assets to delete from onyo'
    )
    # subcommand "fsck"
    cmd_fsck = subcommands.add_parser(
        'fsck',
        help='Checks the consistency and validity of the onyo repository and its contents'
    )
    cmd_fsck.set_defaults(run=commands.fsck)
    return parser


def main():
    parser = parse_args()
    args = parser.parse_args()

    # if ONYO_REPOSITORY_DIR as environmental variable is set, uses it as
    # default onyo dir, otherwise it uses the current working directory as
    # default, but this can always be overwritten by terminal.
    onyo_root = os.environ.get('ONYO_REPOSITORY_DIR')
    if onyo_root is None:
        onyo_root = os.getcwd()

    # TODO: Do onyo fsck here, test if .onyo exists, is git repo, other checks

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
