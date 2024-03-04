Concepts and Terms
==================

Just Files and Folders
**********************

Everything is based on text files and folders. This simplicity makes Onyo
adaptable to alternate layouts and workflows beyond what was imagined when
designing it.

Folders denote assignment: *where* something is or *who* has it.

Inventory Concepts
******************

**Tracking** involves *where* something is or who is belongs to. In an Onyo
repository, every asset is tracked. In file system terms, this means that every
file (asset) is in a folder (named after a location or person). A common example
is a power adapter; it is unimportant to know which exact adapter someone has,
but it is desired to know that a user has one.

**Identification** is when the specificity of an asset is important. For
example: one may wish to know that a user has a specific laptop (e.g. the
MacBook Pro with the inventory number ``ABC123``).

The identify of assets is tracked via its **serial** (see "Asset Name Scheme").

Asset Name Scheme
*****************

Onyo asset names use by default the following pattern:

.. code::

   type_make_model.serial

**Type**: The type of asset (e.g. laptop, display, PDU, etc)

**Make**: The manufacturer/brand (e.g. Lenovo, Apple, Supermicro, etc)

**Model**: The model (e.g. RX2135 or MBPlate2020). User preferences will vary
widely here. Some will wish to use the user-friendly model names (e.g. NUC8),
the precise manufacturer model (BOXNUC8I5BEK2), or their own naming convention.

**Serial**: A unique identifier for the asset. Assets for which the **identity**
is important will use either an inventory number (if present) or manufacturer
serial number (if present).

Assets for which the identity is *not* important receive a unique
**faux-serial** to prevent filename conflicts. These serials are prepended with
the word ``faux``.

Uniqueness
**********

Each filename is unique within the repository. The **serial** alone *should* be
unique, but cross-manufacturer conflicts is theoretically possible. In practice,
the combination of type, make, model, and serial is sufficient to avoid all
(reasonable) chance of conflicts.

File Contents
*************

Files are written in YAML and contain metadata about the asset. This can
describe the physical attributes of the hardware (CPU type, RAM size, etc), but
can also extend to any metadata you wish to track (software, associated purchase
order numbers, etc).

Config Files
************

Configuration files are stored in the ``.onyo/`` folder in the top-level of the
repository.

- ``.onyo/config`` specifies:

  - tools used by ``onyo history``.
    The values can be updated with e.g.:

    - ``onyo config history.interactive "tig --follow"``
    - ``onyo config history.non-interactive "git --no-pager log --follow"``

  - default template to use with ``onyo new --path <asset>``
    The standard template can be updated with e.g.:

    - ``onyo config template.default empty``

- ``.onyo/templates/`` contains:

  - the templates for the ``onyo new --template <template>`` command (see
    "Template Files")

Template Files
**************

Templates can be used with the command ``onyo new --template <template>
--path <asset>`` and are stored in the folder ``.onyo/templates/``.
Templates will be copied as a basis for a new asset file, and can then be
edited. After saving the newly created asset, the file will be checked for
valid YAML syntax.

The default template that gets used when ``onyo new`` is called is
``.onyo/templates/empty``. It can be updated with
``onyo config template.default empty``.

For examples, see the section "Templates" in :doc:`examples`.

Environment Variables
*********************

- ``EDITOR``:

  The text editor spawned by Onyo.
