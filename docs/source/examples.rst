Examples
========

Basic Use
*********

**Inventory a new asset; add it to the shelf:**

.. code:: shell

   onyo new shelf
   <type>*: laptop
   <make>*: lenovo
   <model>*: T490s
   <serial>*: abc123
   <spawns editor. The user edits fields>
   <writes out to shelf/laptop_lenovo_T490s.abc123

**Assign an asset:**

.. code:: shell

   onyo mv shelf/laptop_lenovo_T490s.abc123 accounting/Bingo\ Bob/

**Retire an asset:**

.. code:: shell

   onyo mv accounting/Bingo\ Bob/laptop_lenovo_T490s retired/

**Upgrade an asset:**

.. code:: shell

   onyo set RAM=16GB accounting/Bingo\ Bob/laptop_lenovo_T490s
   - RAM: 8GB
   + RAM: 16GB

or

.. code:: shell

   onyo edit accounting/Bingo\ Bob/laptop_lenovo_T490s
   <spawns $EDITOR; user edits RAM field>

**List all assets on the shelf:**

.. code:: shell

   onyo tree shelf

**List the history of an asset:**

.. code:: shell

   onyo history accounting/Bingo\ Bob/laptop_lenovo_T490s

**List the history of all assets of a user:**

.. code:: shell

   onyo history accounting/Bingo\ Bob

Templates
*********

This section describes some of the templates provided with ``onyo init`` in the
directory ``.onyo/templates/``.

``onyo new <dir>`` (equivalent to ``onyo new --template standard <dir>``) as defined
by ``.onyo/templates/standard`` is a plain YAML file:

.. code:: yaml

   ---

This template passes the YAML syntax check when onyo is called while the editor
is suppressed with ``onyo new --non-interactive <directory>``.

``onyo new --template laptop.example <dir>`` as defined by
``.onyo/templates/laptop.example`` contains a simple example for a laptop asset
which already contains some fields, which are relevant for all assets of that
device type.

.. code:: yaml

   ---
   RAM:
   Size:
   USB:
