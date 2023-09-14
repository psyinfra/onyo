from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import fsck, new as new_cmd
from onyo.argparse_helpers import template, path, StoreKeyValuePairs
from onyo.shared_arguments import shared_arg_message


if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')

args_new = {

    'template': dict(
        args=('-t', '--template'),
        metavar='TEMPLATE',
        required=False,
        type=template,
        help='Name of the template to seed the new asset(s)'),

    'edit': dict(
        args=('-e', '--edit'),
        required=False,
        default=False,
        action='store_true',
        help='Open new assets in editor before creation'),

    'keys': dict(
        args=('-k', '--keys'),
        required=False,
        action=StoreKeyValuePairs,
        metavar="KEYS",
        nargs='+',
        help=(
            'Key-value pairs to set in the new asset(s). Multiple pairs can be '
            'specified (e.g. key=value key2=value2)')),

    'path': dict(
        args=('-p', '--path'),
        metavar='ASSET',
        type=path,
        nargs='*',
        help='Path(s) of the new asset(s). Excludes usage of --tsv'),

    'tsv': dict(
        args=('-tsv', '--tsv'),
        metavar='TSV',
        required=False,
        type=path,
        help=('Path to a tsv file describing the new asset. Excludes the usage '
              'of --path')),

    'message': shared_arg_message,
}


def new(args: argparse.Namespace) -> None:
    """
    Create new ``DIRECTORY/ASSET``\\(s), and add contents with ``--template``,
    ``--keys`` and ``--edit``. If the directories do not exist, they will be
    created.

    After the contents are added, the new ``assets``\\(s) will be checked for
    the validity of its YAML syntax.
    """
    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo)
    path = [Path(p).resolve() for p in args.path] if args.path else None
    tsv = Path(args.tsv).resolve() if args.tsv else None
    new_cmd(repo, path, args.template, tsv, args.keys, args.edit, args.yes, args.message)
