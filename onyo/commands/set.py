from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.inventory import Inventory
from onyo.lib.commands import onyo_set
from onyo.argparse_helpers import path, StoreKeyValuePairs
from onyo.shared_arguments import (
    shared_arg_depth,
    shared_arg_filter,
    shared_arg_message,
)

if TYPE_CHECKING:
    import argparse

args_set = {
    'rename': dict(
        args=('-r', '--rename'),
        required=False,
        default=False,
        action='store_true',
        help=(
            'Permit assigning values to pseudo-keys that would result in the '
            'asset(s) being renamed.')),

    'keys': dict(
        args=('-k', '--keys'),
        required=True,
        action=StoreKeyValuePairs,
        metavar="KEYS",
        nargs='+',
        help=(
            'Specify key-value pairs to set in asset(s). Multiple pairs can '
            'be specified (e.g. key=value key2=value2)')),

    'path': dict(
        args=('-p', '--path'),
        metavar='PATH',
        nargs='*',
        type=path,
        help='Asset(s) and/or directorie(s) to set KEY=VALUE in'),

    'depth': shared_arg_depth,
    'filter': shared_arg_filter,
    'message': shared_arg_message,
}


def set(args: argparse.Namespace) -> None:
    """
    Set the ``value`` of ``key`` for matching assets. If a key does not exist,
    it is added and set appropriately.

    Key names can be any valid YAML key name.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    Required keys as defined by the 'onyo.assets.filename' config (by default
    ``type``, ``make``, ``model``, and ``serial``) can be set when the
    `--rename` flag is used. It will result in the file(s) being
    renamed.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used. If Onyo is invoked from outside of the Onyo repository, the root of
    the repository is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    paths = [Path(p).resolve() for p in args.path] if args.path else None
    # TODO: The following check should be incorporated in the argparse Action.
    #       IOW: This requires a variant of StoreKeyValuePairs, that does not
    #       allow for key duplication (and can tell which keys are affected)
    if len(args.keys) > 1:
        raise ValueError("Keys must not be given multiple times.")
    onyo_set(inventory=inventory,
             paths=paths,
             keys=args.keys[0],
             filter_strings=args.filter,
             rename=args.rename,
             depth=args.depth,
             message='\n\n'.join(m for m in args.message) if args.message else None)
