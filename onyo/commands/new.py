from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import template, path, StoreKeyValuePairs
from onyo.lib.commands import onyo_new
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

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
        metavar='PATH',
        type=path,
        help='directory to create asset(s) in'),

    'tsv': dict(
        args=('-tsv', '--tsv'),
        metavar='TSV',
        required=False,
        type=path,
        help='Path to a tsv file describing the new asset.'),

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
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_new(inventory=inventory,
             path=Path(args.path).resolve() if args.path else None,
             template=args.template,
             tsv=Path(args.tsv).resolve() if args.tsv else None,
             keys=args.keys,
             edit=args.edit,
             message='\n\n'.join(m for m in args.message) if args.message else None)
