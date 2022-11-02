Changelog
=========

Next
****

Changes listed here will be part of the next release.

--------------------------------------------------------------------------------

0.3.0 (2022.11.02)
******************
This release introduces an Onyo API and contains general code modernization,
performance improvements, and expansion of tests.

The highlights are:

Command Changes
---------------
- ``onyo mv --rename`` is retired. ``onyo set`` is the only command that can
  change keys/pseudo-keys.
- add ``onyo mv --quiet``
- rename ``onyo mv --force`` to ``onyo mv --yes`` to match other commands
- ``onyo new`` faux serials default length is decreased from 8 to 6
- asset read/write always preserves key order and comments (aka: roundtrip mode)

API
---
- a new ``Repo`` class to represent a repository as an object
- ``Repo(init=True)`` initializes a new repository
- the following properties are added to ``Repo``:

  - ``assets``: assets in the repo
  - ``dirs``: directories in the repo
  - ``files``: files in the repo
  - ``files_changed``: files in the "changed" state in git
  - ``files_staged``: files in the "staged" state in git
  - ``files_untracked``: files "untracked" by git
  - ``root``: repository root
  - ``opdir``: operating directory

- the following public methods are added to ``Repo``:

  - ``Repo.add()``: stage a file's changed contents
  - ``Repo.commit()``: commit all staged changes
  - ``Repo.generate_faux_serials()``: generate unique, fake serials
  - ``Repo.get_config()``: get a config value
  - ``Repo.set_config()``: set a config name and value, in either ``.onyo/config``
    or any other valid git-config location
  - ``Repo.fsck()``: fsck the repository, individual tests can be selected
  - ``Repo.mkdir()``: create a directory (and any parents), add ``.anchor`` files,
    and stage them
  - ``Repo.mv()``: move/rename a directory/file and stage it
  - ``Repo.rm()``: delete a directory/file and stage it

- remove ``onyo/utils.py``
- most tests are rewritten/updated to be self-contained

Bugs
----
- ``onyo history`` honors ``onyo -C``
- ``onyo history`` errors bubble up the correct exit code
- "protected paths" (such as ``.anchor``, ``.git``, ``.onyo``) are checked
  for anywhere in the path name.
- calling ``onyo`` with an insufficient number of arguments no longer exits 0
- arguments named 'config' no longer ignore subsequent arguments
- simultaneous use of ``onyo -C`` and ``onyo --debug`` no longer crashes Onyo
- faux serials are generated in a more random way
- ``onyo mkdir`` no longer errors with overlapping target directories
- ``onyo mv file-1 subdir/file-1`` (aka: explicit move) no longer errors

Validation
----------
Validation is entirely removed. It will be reintroduced, in an improved form, in
a later release.

Docs
----
Linting is documented.

Tests
-----
- add tests for the ``onyo edit`` command
- add tests for the ``onyo history`` command
- add tests for the ``onyo mv`` command
- add tests for the ``onyo new`` command
- add tests for the ``onyo`` command
- add tests for the ``Repo`` class:

  - initialization
  - instantiation
  - ``assets``
  - ``dirs``
  - ``files``
  - ``files_changes``
  - ``files_staged``
  - ``files_untracked``
  - ``root``
  - ``opdir``
  - ``add()``
  - ``commit()``
  - ``generate_faux_serials()``
  - ``get_config()``
  - ``set_config()``
  - ``fsck()``
  - ``mkdir()``
  - ``mv()``
  - ``rm()``

- `Pyre <https://pyre-check.org/>`_ is used for type checking
- ``repo`` fixture to assist with test setup and isolation

Installation
------------
The Python version required by Onyo is bumped from 3.7 to 3.9.

Both GitPython and PyYAML are dropped as dependencies.

Authors
-------
-  Tobias Kadelka (`@TobiasKadelka <https://github.com/TobiasKadelka>`__)
-  Alex Waite (`@aqw <https://github.com/aqw>`__)

--------------------------------------------------------------------------------

0.2.0 (2022.09.28)
******************
This release primarily focused on configuration, refactoring, and tests.

The highlights are:

Command Changes
---------------
- ``onyo cat``: error codes are now reliably reported and bugs related to
  roundtrip-ing were fixed
- ``onyo config``: now calls ``git config`` and thus inherits all of its
  functionality (with a few intentional exceptions).
- ``onyo shell-completion``: now supports completion for ``onyo -C``,
  ``onyo config``, ``onyo new --templates``, and when Onyo is invoked through an
  alias.

Retired
-------
- ``onyo git``: retired in favor of aliasing ``onyo-git`` (see :ref:`aliases`).

Configuration
-------------
Configuration was completed overhauled:

- options can be set in either ``git config`` or ``onyo config``
- all options are moved into an ``onyo`` namespace.
- added ``onyo.core.editor`` to configure the preferred editor
- documentation written (see :doc:`configuration`)

Docs
----
- configuration is documented (see :doc:`configuration`)
- help output is stripped of various rst-isms
- documented using aliases with onyo, especially to operate on an onyo repo from
  elsewhere on the system
- improved documentation for building and testing

Tests
-----
- enabled code coverage
- many tests added, notably for ``onyo cat`` and ``onyo config``
- significant refactoring and cleanup

Authors
-------
-  Alex Waite (`@aqw <https://github.com/aqw>`__)
-  Laura Waite (`@loj <https://github.com/loj>`__)

--------------------------------------------------------------------------------

0.1.0 (2022.09.19)
******************
Onyo still isn't ready for production use yet, but it has gained a lot of
features, fixes, documentation, and tests since the last release.

The highlights are:

New Commands
------------
- ``onyo config``: configure options
- ``onyo fsck``: check the sanity of the git repo, onyo config, and validate all
  assets
- ``onyo history``: see the history of an asset or directory (spawns ``tig`` or
  ``git log``)
- ``onyo mkdir``: create directories (with ``.anchor`` files)
- ``onyo rm``: delete assets and directories
- ``onyo set``: set keys and values in assets
- ``onyo shell-completion``: tab-completion support

Command Changes
---------------
- ``onyo new``:

  - a faux-serial number is generated when the serial field is left blank
  - spawns an editor after initial dialog
  - support for templates (see :ref:`templates`)
- ``onyo new`` and ``onyo edit``: now check for valid YAML and passing
  validation rules
- ``onyo new`` and ``onyo mkdir``: no longer automatically create missing parent
- most commands now accept multiple files and directories as arguments
- most commands now verify the integrity of the repo before executing

Retired
-------
- ``onyo anchor`` and ``onyo unanchor``: these were retired in favor of
  ``onyo mkdir`` which always creates an ``.anchor`` file.
- ``ONYO_REPOSITORY_DIR``: ``onyo -C`` should be used instead

Validation
----------
Rudimentary validation support is now available for the contents of asset files.
It's currently mostly limited to checking types, but will be expanded for more
sophisticated checks.

When invoking ``onyo edit`` or ``onyo new``, the file must pass validation
before it will be saved and committed.

Docs
----
- Command descriptions have been moved from the README into Onyo and are
  available when invoking ``--help``.
- The help text has received a lot of attention to improve clarity and also
  consistency of language across commands.
- Read the Docs has been setup, and content migrated to it.

Art
---
Onyo has a logo!

Tests
-----
- RTD runs a test-build for all PRs
- A boatload of new tests have been written
- The tests no longer run in the top-level and now create ``tests/sandbox``

Installation
------------
Onyo now requires Python 3.7 or newer.

Authors
-------
-  Anne Ghisla (`@aghisla <https://github.com/aghisla>`__)
-  Tobias Kadelka (`@TobiasKadelka <https://github.com/TobiasKadelka>`__)
-  Alex Waite (`@aqw <https://github.com/aqw>`__)
-  Laura Waite (`@loj <https://github.com/loj>`__)

--------------------------------------------------------------------------------

0.0.1 (2022.03.24)
******************
Onyo lives! It's still the beginning --- and Onyo explodes more often than it
should --- but the overall design has been written, and the commands are taking
shape.

The highlights are:

New Commands
------------
- ``onyo anchor`` and ``onyo unanchor``: add/remove an ``.anchor`` file in
  directories, so that they can be tracked by git
- ``onyo cat``: print assets to stdout
- ``onyo edit``: edit assets
- ``onyo init``: initialize an onyo repo
- ``onyo mv``: move assets and directories
- ``onyo new``: create new assets
- ``onyo tree``: print a directories/files in a tree structure
- ``onyo git``: run git commands from within the onyo repo (most useful with
  ``onyo -C`` or ``ONYO_REPOSITORY_DIR``)
- ``onyo --debug``: debug logging

Tests
-----
- Basic tests and CI

Authors
-------
-  Tobias Kadelka (`@TobiasKadelka <https://github.com/TobiasKadelka>`__)
-  Alex Waite (`@aqw <https://github.com/aqw>`__)
