onyo new
========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: new


Example Usage
*************

**Add new assets**

Use ``onyo new`` to add a new asset and add some content to it:

.. code:: shell

   onyo new --keys RAM=8GB display=14.6 --path shelf/laptop_lenovo_T490s.abc123

This command writes a YAML file to ``shelf/laptop_lenovo_T490s.abc123``:

.. code:: shell

   RAM: 8GB
   display: 14.6

Create multiple new assets with content, and overwrite the default message
with a more helpful one describing the action:

.. code:: shell

   onyo new --keys RAM=16GB display_size=14.6 touch=yes
   --message "devices for the new group are delivered"
   --path shelf/laptop_lenovo_T490s.abc123 shelf/laptop_lenovo_T490s.abc456
   admin/Karl/laptop_apple_macbookpro.222 admin/Theo/laptop_apple_macbookpro.17


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

    display: 13.3
    usb_ports: 2


**Use pre-filled templates and adjust them to add new assets**

To facilitate the creation of many similar devices, add templates under
``.onyo/templates/`` and use them with ``onyo new --template <template>``.

``onyo new --edit --template laptop_lenovo
--path shelf/laptop_apple_macbookpro.0io4ff`` adds a new macbook to the
inventory with the template ``.onyo/templates/laptop_lenovo``:

.. code:: yaml

   ---
   RAM: 16GB
   Size: 14.6
   USB: 3

The command copies the contents of the template file into the asset
``shelf/laptop_apple_macbookpro.0io4ff``, and then the ``--edit`` flag opens the
editor to add or adjust missing information.
