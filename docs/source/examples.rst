Examples
========

An inventory managed with Onyo
******************************

The repository https://github.com/psyinfra/onyo-demo shows an example of how a
full inventory with many assets and directories, which was generated and managed
with Onyo, can look like.

Basic Use
*********

**Inventory a new asset; add it to the shelf:**

.. code:: shell

   onyo new --keys RAM=8GB --path shelf/laptop_lenovo_T490s.abc123
   <writes out to shelf/laptop_lenovo_T490s.abc123>

**Assign an asset:**

.. code:: shell

   onyo mv shelf/laptop_lenovo_T490s.abc123 accounting/Bingo\ Bob/

**Retire an asset:**

.. code:: shell

   onyo mv accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123 retired/

**Upgrade an asset:**

.. code:: shell

   onyo set --keys RAM=16GB --path accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123
   - RAM: 8GB
   + RAM: 16GB

or

.. code:: shell

   onyo edit accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123
   <spawns $EDITOR; user edits RAM field>

**List all assets on the shelf:**

.. code:: shell

   onyo tree shelf

**List the history of an asset:**

.. code:: shell

   onyo history accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

**List the history of all assets of a user:**

.. code:: shell

   onyo history accounting/Bingo\ Bob

Templates
*********

This section describes some of the templates provided with ``onyo init`` in the
directory ``.onyo/templates/``.

``onyo new --path <asset>`` (equivalent to
``onyo new --template empty --path <asset>``) as defined
by ``.onyo/templates/empty`` is an empty YAML file.

This template passes the YAML syntax check when onyo is called while the editor
is suppressed with ``onyo new --non-interactive --path <asset>``.

``onyo new --template laptop.example --path <asset>`` as defined by
``.onyo/templates/laptop.example`` contains a simple example for a laptop asset
which already contains some fields, which are relevant for all assets of that
device type.

.. code:: yaml

   ---
   RAM:
   Size:
   USB:
