onyo new
========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: new


Reserved keys
*************

Onyo reserves some keys which have a special function when used while creating
new assets, either with ``onyo new --keys`` or in a tsv table with
``onyo new --tsv``.
They can be used multiple times with different values to create multiple
new assets at once with a different value for each asset.

**directory**

    The ``directory`` key is an alternative to ``onyo new --directory`` to specify
    the location in which to create new assets.

**template**

    The ``template`` key is an alternative to ``onyo new --template`` to specify
    which template to use to create new assets.


Example Usage
*************

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
