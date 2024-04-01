from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.argparse_helpers import StoreMultipleKeyValuePairs
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
        help=r"""
            Path of an asset to clone.

            This cannot be used with the ``--template`` flag nor the
            ``template`` Reserved Key.
        """
    ),

    'template': dict(
        args=('-t', '--template'),
        metavar='TEMPLATE',
        required=False,
        help=r"""
            Name of a template to populate the contents of new assets.

            This cannot be used with the ``--clone`` flag nor the ``template``
            Reserved Key.
        """
    ),

    'tsv': dict(
        args=('-tsv', '--tsv'),
        metavar='TSV',
        required=False,
        help=r"""
            Path to a **TSV** file describing new assets.

            The header declares the key names to be populated. The values to
            populate assets are declared with one line per asset.
        """
    ),

    'keys': dict(
        args=('-k', '--keys'),
        required=False,
        action=StoreMultipleKeyValuePairs,
        metavar="KEY",
        nargs='+',
        help=r"""
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
        help=r"""
            Open new assets in an editor.
        """
    ),

    'directory': dict(
        args=('-d', '--directory'),
        metavar='DIRECTORY',
        help=r"""
            Directory to create new assets in.

            This cannot be used with the ``directory`` Reserved Key.
        """
    ),

    'message': shared_arg_message,
}

epilog_new = r"""
.. rubric:: Examples

**Add new assets**

Use ``onyo new`` to add a new asset and add some content to it:

.. code:: shell

   onyo new --keys RAM=8GB display=14.6 type=laptop make=lenovo model=T490s serial=abc123 --directory shelf/

This command writes a YAML file to ``shelf/laptop_lenovo_T490s.abc123``:

.. code:: shell

   RAM: 8GB
   display: 14.6
   type: laptop
   make: lenovo
   model: T490s
   serial: abc123

**Create multiple new assets with content in different locations, and overwrite
the default message**

.. code:: shell

   onyo new --keys RAM=16GB display_size=14.6 touch=yes
   type=laptop make=lenovo model=T490s serial=abc123 directory=Bingo\ Bob
   type=laptop make=apple model=macbookpro serial=abc456 directory=Alice\ Wonderland
   type=laptop make=apple model=macbookpro serial=17 directory=shelf
   --message "devices for the new group are delivered"


**Add inventory with a table**

To add many different assets, instead of calling ``onyo new`` multiple times
with different arguments, use a tsv table to describe the new devices:

.. code:: shell

   onyo new  --keys usb_ports=2 --tsv demo/inventory.tsv

With ``inventory.tsv`` being:

+--------+-------+------------+--------+------------------+---------+
| type   | make  | model      | serial | directory        | display |
+========+=======+============+========+==================+=========+
| laptop | apple | macbookpro | 0io4ff | warehouse        | 13.3    |
+--------+-------+------------+--------+------------------+---------+
| laptop | apple | macbookpro | 1eic93 | warehouse        | 13.3    |
+--------+-------+------------+--------+------------------+---------+
| laptop | apple | macbookpro | j7tbkk | repair           | 13.3    |
+--------+-------+------------+--------+------------------+---------+
| laptop | apple | macbookpro | dd082o | repair           | 13.3    |
+--------+-------+------------+--------+------------------+---------+
| laptop | apple | macbookpro | 9sdjwa | admin/Karl Krebs | 13.3    |
+--------+-------+------------+--------+------------------+---------+


The columns type, make, model and serial define the asset name, and the column
path sets the location were asset will be created (e.g.
``warehouse/laptop_apple_macbookpro.0io4ff``). The rest of the information (the
column ``display`` and the key value pair ``usb_ports=2`` from the CLI call)
will be written into the asset file
``warehouse/laptop_apple_macbookpro.0io4ff``:

.. code:: shell

    type: laptop
    make: apple
    model: macbookpro
    serial: 0io4ff
    display: 13.3
    usb_ports: 2


**Use pre-filled templates and adjust them to add new assets**

To facilitate the creation of many similar devices, add templates under
``.onyo/templates/`` and use them with ``onyo new --template <template>``.

``onyo new --edit --template laptop_lenovo --directory shelf/`` adds a new laptop to
the inventory, using ``.onyo/templates/laptop_lenovo`` as a pre-filled template:

.. code:: yaml

   ---
   type: laptop
   make: lenovo
   model:
   serial:
   RAM: 16GB
   Size: 14.6
   USB: 3

The command copies the contents of the template file into the new asset, and
then the ``--edit`` flag opens the editor to add or adjust missing information.
"""


def new(args: argparse.Namespace) -> None:
    r"""
    Create new **ASSET**\ s and populate with **KEY-VALUE** pairs. Destination
    directories are created if they are missing.

    Asset contents are populated in a waterfall pattern and can overwrite
    values from previous steps:

      1) ``--clone`` or ``--template``
      2) ``--tsv``
      3) ``--keys``
      4) ``--edit`` (i.e. manual user input)

    The **KEY**\ s that comprise the asset filename are required (configured by
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
