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

Validation
**********

The following sections give examples how one can use the ``validation.yaml`` to
keep assets and their metadata consistent in an onyo repository. Onyo reads the
``validation.yaml`` file from top to bottom and will apply the first rule for
which the name scheme fits an asset.

**Example 1: Rules for different files and directories**

For each directory/path, a separate set of rules can be specified (e.g.
``shelf/*`` and ``user1/*``). The user can also define rules, that just apply to
files, that match certain asset names (``shelf/*laptop*`` in the example).

.. code:: yaml

   "shelf/*laptop*":
   - RAM:
       - Type: int
   "shelf/*":
   - RAM:
       - Type: float
   "user1/*":
   - Size:
       - Type: int
   - USB:
       - Type: int

For the assets in ``shelf`` with "laptop" in their file name, the value RAM must
have the type int. All other assets in ``shelf`` can have a float as RAM value.
For assets under the directory ``user1/*`` the rules for the RAM key do not
apply, instead it has a different set of rules for the keys ``Size`` and
``USB``.

**Example 2: Directories, Sub-Directories and onyo-wide Rules**

Onyo differentiates between ``shelf/*`` (to define rules for assets directly
under ``shelf/``) and ``shelf/**`` (for all assets in shelf and all its
sub-directories).  The user can also use ``"**":`` at the end of
``validation.yaml`` to specify a set of rules that will be applied to all assets
anywhere in onyo, if no other rule defined before applies to an asset file.

.. code:: yaml

   "shelf/*":
   - RAM:
       - Type: int
   "shelf/**":
   - Size:
       - Type: int
   "**":
   - RAM:
       - Type: float
   - Size:
       - Type: float

When assets directly in ``shelf/`` have a key ``RAM``, it must be integer.
Because onyo uses just the first set of rules where the asset matches the path
defined in validation.yaml, the later rules under ``shelf/**`` do not apply to
assets directly in ``shelf/``.

When assets are in a sub-folder of ``shelf/``, the rule for RAM does not apply,
instead the separate set of rules under ``shelf/**`` will be used to validate
these assets.

Asset files in sub-directories of shelf, e.g. ``shelf/left/top_row/`` have no
rules regarding the ``RAM`` key, just the rule for ``Size`` does apply.

The rule ``**`` enforces for all assets outside of ``shelf/`` that keys for RAM
and Size must be at least float (e.g. "RAM: 12GB" as string are invalid for all
assets anywhere in the onyo repository).

The rules for ``**`` do not apply to assets in ``shelf/``, because onyo uses
just the first set of rules where a path matches, and ``shelf/`` has a separate
set of rules already defined above.

**Example 3: Using pointer to define a set of rules for multiple Directories**

To define a single set of rules, that is applied to multiple other directories
(users in the example), YAML pointers can be used.

.. code:: yaml

   "generic_rules_for_users/**": &pointer_user
   - RAM:
       - Type: int
   - Size:
       - Type: int
   "user1/**":
       *pointer_user
   "user2/**":
       *pointer_user

A generic set of rules can be defined and marked with ``&pointer_user``, to
enable the usage of the set of rules for other directories. With
``*pointer_user`` the rules for ``RAM`` and ``Size`` will be a applied for the
directories ``user1/**`` and ``user2/**``.
