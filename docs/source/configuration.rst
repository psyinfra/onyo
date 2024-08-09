Configuration
=============

Onyo configuration options can be set locally using ``git config`` or tracked in
the repository using ``onyo config``.

* ``git config`` should be used for preferences of only local relevance, such as
  ``onyo.core.editor``.

* ``onyo config`` stores values in ``.onyo/config`` which is tracked in the
  repository. These settings are shared with all consumers of an Onyo
  repository, making it useful for configuration related to common workflows,
  such as ``onyo.new.template``.

Within the Onyo code, configuration options are read in the following order of
precedence:

#. git config (which follows git's own order of precedence: system, global, and
   repository local configuration files)
#. onyo config


Options
*******

``onyo.core.editor``
    The editor to use for commands such as ``edit`` and ``new``. If unset, it
    will fallback to ``core.editor`` configuration of ``git`` it self, then to
    the environmental variable ``EDITOR`` and lastly ``nano``.
    (default: unset)

``onyo.history.interactive``
    The command used to display history when running ``onyo history``. (default:
    ``tig --follow``)

``onyo.history.non-interactive``
    The command used to print history when running ``onyo history`` with
    ``--non-interactive``.  (default: ``git --no-pager log --follow``)

``onyo.new.template``
    The default template to use with ``onyo new``. (default: "empty")

``onyo.assets.filename``
    The name scheme for asset files and asset directories in the repository.
    (default: "{type}_{make}_{model}.{serial}")

``onyo.repo.version``
	The version of the onyo repository.

.. _templates:

Templates
*********

This section describes some of the templates provided with ``onyo init`` in the
directory ``.onyo/templates/``.

``onyo new --keys <keys> --path <directory>`` (equivalent to
``onyo new --keys <keys> --template empty --path <directory>``) as defined
by ``.onyo/templates/empty`` is an empty YAML file, and ``keys`` must
additionally specify the keys used for asset names.

``onyo new --edit --template laptop.example --path <directory>`` as defined by
``.onyo/templates/laptop.example`` contains a simple example for a laptop asset
which already contains some fields, which are relevant for all assets of that
device type.

.. code:: yaml

   ---
   type:
   make:
   model:
   serial:
   RAM:
   Size:
   USB:
