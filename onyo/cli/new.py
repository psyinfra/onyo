from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.argparse_helpers import StoreKeyValuePairs
from onyo.lib.commands import onyo_new
from onyo.lib.inventory import Inventory
from onyo.shared_arguments import shared_arg_message

if TYPE_CHECKING:
    import argparse

args_new = {

    'clone': dict(
        args=('-c', '--clone'),
        metavar='CLONE',
        required=False,
        help="""
            Path of an asset to clone.

            This cannot be used with the ``--template`` flag nor the
            ``template`` Reserved Key.
        """
    ),

    'template': dict(
        args=('-t', '--template'),
        metavar='TEMPLATE',
        required=False,
        help="""
            Name of a template to populate the contents of new assets.

            This cannot be used with the ``--clone`` flag nor the ``template``
            Reserved Key.
        """
    ),

    'tsv': dict(
        args=('-tsv', '--tsv'),
        metavar='TSV',
        required=False,
        help="""
            Path to a **TSV** file describing new assets.

            The header declares the key names to be populated. The values to
            populate assets are declared with one line per asset.
        """
    ),

    'keys': dict(
        args=('-k', '--keys'),
        required=False,
        action=StoreKeyValuePairs,
        metavar="KEY",
        nargs='+',
        help="""
            **KEY-VALUE** pairs to populate content of new assets.

            Each **KEY** can be defined either 1 or N times (where N is the number
            of assets to be created). A **KEY** that is declared once will apply
            to all new assets, otherwise each will be applied to each new asset
            in the order they were declared.

            For example, create three new laptops with different serials:
            ```
            $ onyo new --keys type=laptop make=apple model=macbookpro serial=1 serial=2 serial=3 --directory shelf/
            ```

            Shell brace-expansion makes this even more succinct:
            ```
            $ onyo new --keys type=laptop make=apple model=macbookpro serial={1,2,3} --directory shelf/
            ```
        """
    ),

    'edit': dict(
        args=('-e', '--edit'),
        required=False,
        default=False,
        action='store_true',
        help="""
            Open new assets in an editor.
        """
    ),

    'directory': dict(
        args=('-d', '--directory'),
        metavar='DIRECTORY',
        help="""
            Directory to create new assets in.

            This cannot be used with the ``directory`` Reserved Key.
        """
    ),

    'message': shared_arg_message,
}


def new(args: argparse.Namespace) -> None:
    """
    Create new **ASSET**\s and populate with **KEY-VALUE** pairs. Destination
    directories are created if they are missing.

    Asset contents are populated in a waterfall pattern and can overwrite
    values from previous steps:

      1) ``--clone`` or ``--template``
      2) ``--tsv``
      3) ``--keys``
      4) ``--edit`` (i.e. manual user input)

    The **KEY**\s that comprise the asset filename are required (configured by
    ``onyo.assets.filename``).

    The contents of all new assets are checked for validity before committing.

    RESERVED KEYS:

    Some key names are reserved, and are not stored as keys in asset contents:

      * ``directory``: directory to create the asset in relative to the root of
        the repository. This key cannot be used with the ``--directory`` flag.
      * ``is_asset_directory``: whether to create the asset as an Asset
        Directory.  Default is ``false``.
      * ``template``: which template to use for the asset. This key cannot be
        used with the ``--clone`` or ``--template`` flags.
    """
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_new(inventory=inventory,
             directory=Path(args.directory).resolve() if args.directory else None,
             template=args.template,
             clone=Path(args.clone).resolve() if args.clone else None,
             tsv=Path(args.tsv).resolve() if args.tsv else None,
             keys=args.keys,
             edit=args.edit,
             message='\n\n'.join(m for m in args.message) if args.message else None)
