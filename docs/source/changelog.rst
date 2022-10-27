Changelog
=========

Next
****

Changes listed have been merged into Onyo and will be part of the next release.

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
