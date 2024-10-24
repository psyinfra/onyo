from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.argparse_helpers import StoreSingleKeyValuePairs
from onyo.lib.commands import onyo_set
from onyo.lib.inventory import Inventory
from onyo.lib.onyo import OnyoRepo
from onyo.shared_arguments import (
    shared_arg_message,
    shared_arg_no_auto_message,
)

if TYPE_CHECKING:
    import argparse

args_set = {
    'keys': dict(
        args=('-k', '--keys'),
        required=True,
        action=StoreSingleKeyValuePairs,
        metavar="KEY",
        nargs='+',
        help=r"""
            **KEY-VALUE** pairs to set in assets. Multiple pairs can be given
            (e.g. ``key1=value1 key2=value2 key3=value3``).

            Quotes are necessary when using spaces or shell command characters:
            ```
            $ onyo set --keys title='Bob Bozniffiq: Saint of the Awkward' --asset ...
            ```

            Dictionary subkeys can be addressed using a period (e.g. ``model.name``,
            ``model.year``, etc.)
        """
    ),

    'asset': dict(
        args=('-a', '--asset'),
        required=True,
        metavar='ASSET',
        nargs='+',
        help=r"""
            Assets to set **KEY-VALUE**\ s in.
        """
    ),

    'message': shared_arg_message,
    'no_auto_message': shared_arg_no_auto_message,
}

epilog_set = r"""
.. rubric:: Examples

Upgrade an asset:

.. code:: shell

    $ onyo set --keys RAM=16GB --asset accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

Change a key used in the asset name (thus renaming it):

.. code:: shell

    $ onyo set --keys type=notebook --asset accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

Change the model name of all "mbp" to "macbookpro":

.. code:: shell

    $ onyo get --machine-readable --match model=macbookpro --keys path \
           | xargs -d "\n" onyo --yes set --keys model=mbp --asset

Change an Asset File to an Asset Directory:

.. code:: shell

    $ onyo set --keys is_asset_directory=true --asset accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123
"""


def set(args: argparse.Namespace) -> None:
    r"""
    Set **KEY**\ s to **VALUE**\ s for assets.

    **KEY** names can be any valid YAML key-name. If a key is not present in an
    asset, it is added and set appropriately.

    In addition to keys in asset contents, some PSEUDO-KEYS can be set:

      * ``is_asset_directory``: boolean to control whether the asset is an
        Asset Directory.

    The contents of all modified assets are checked for validity before
    committing. If problems are found, Onyo will error and leave the assets
    unmodified.
    """

    # Note: Replacing special symbols here, that are pointless in the python interface (`onyo_set()`).
    #       Could be done by StoreSingleKeyValuePairs instead, since it's currently only used by `set`.
    #       But we may need it elsewhere, so don't blow its scope.
    symbols_mapping = {'{}': dict(),
                       '<dict>': dict(),
                       '[]': list(),
                       '<list>': list()}
    keys = {k: symbols_mapping[v] if v in symbols_mapping else v
            for k, v in args.keys.items()}
    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    assets = [Path(a).resolve() for a in args.asset]
    onyo_set(inventory=inventory,
             assets=assets,
             keys=keys,
             message='\n\n'.join(m for m in args.message) if args.message else None,
             auto_message=False if args.no_auto_message else None)
