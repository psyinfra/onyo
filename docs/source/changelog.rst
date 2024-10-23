Changelog
=========

Next
****

Changes listed here will be part of the next release.

--------------------------------------------------------------------------------

0.5.0 (2024.10.24)
******************

This release is by far the most substantial in Onyo's brief history. It includes
over a year of development and a significant rearchitecting of Onyo. Pretty much
everything has been changed or improved one way or another.

The highlights are:

Behavior
--------

- All changes are performed in memory or temporary files before being accepted
  by the user. Changes are not longer staged in-repo and (potentially) rolled
  back.
- An Inventory Operations Summary is generated and included in the commit
  message and alongside the diff when prompting the user for review.
- Asset names are now user-definable via the ``onyo.assets.name-format``
  configuration.
- All keys are included in the asset content. Asset names no longer contain
  unique data.
- Diffs are colorized.
- Comments in assets and templates are preserved.
- git's ``core.editor`` is now also considered when selecting an editor.
- All assets start with YAML's (optional) opening header ``---``. This can be
  useful when using ``cat`` on multiple assets, and still yields a valid YAML
  stream.
- Editors are more likely to use YAML syntax highlighting due to the YAML header
  (``---``) and temporary files ending with ``.yaml``.


API
---

- Main entry point now is an ``Inventory`` object. All operations are available
  as methods of this class. Operations are prepared in-memory and are written
  upon ``Inventory.commit()``. All command implementations are build on top of
  this.
- Implementations of Onyo commands are available from ``lib.commands.onyo_*``.
- ``Repo()`` is now split into ``OnyoRepo()`` and ``GitRepo()``

  - Loads of non-repo-related functionality has been split out into separate
    utilities.


Command Changes
---------------

- ``--dry-run`` is removed from all commands. All diffs are done in memory and
  the user is prompted before applying.
- ``-m, --message`` can be passed multiple times, each generating its own
  paragraph (matching git's behavior)
- ``onyo edit`` now prompts for "yes, edit, skip, abort" rather than just "yes,
  no".
- ``onyo get`` no longer always returns the ``path`` key. Only the keys
  specified by ``--keys`` are returned.
- ``onyo get``'s return codes now match ``grep``'s (0 for results, 1 for none
  found, 2 for error).
- ``onyo mkdir`` no longer errors when the target directory exists
- ``onyo new`` can now ``-c, --clone`` from an existing asset (i.e.  use an
  asset as a template).
- ``onyo new --path`` is renamed to ``--directory``.
- ``onyo rm``'s ``--asset`` and ``--dir`` flags are removed.
- ``onyo rm`` is no longer recursive by default, and has a ``--recursive`` flag.
- ``onyo set --rename`` has been removed. Keys that are used in the asset name
  are not considered any more special than other keys.
- ``onyo tree`` now has a ``-d, --dirs-only`` flag.


Pseudo Keys
-----------

Two new pseudo keys have been introduced:

- ``directory``: the parent directory of an asset. Can be queried with ``get``
  or set with ``onyo new`` either in ``--keys`` or TSV file.
- ``is_asset_directory``: see Asset Directories section


Nested Dictionaries
-------------------

Onyo now supports referencing nested dictionaries using a "dot notation" (e.g.
``model.name``). This allows much, much more structure to the data in assets.


Asset Directories
-----------------

Assets can now also be a directory (with the actual content in a hidden file in
the dir). This allows assets to contain assets, such as a server with many hard
drives, network adapters, etc.

All commands have been updated to work with asset directories.

``onyo mkdir`` on an existing asset file will convert it into an asset
directory.

The ``is_asset_directory`` Pseudo Key has been added to query with ``onyo get``
and can also be controlled with ``onyo set`` and ``onyo new``.


Filtering
---------

Filtering has been completely overhauled. It has been removed from all commands
(``set`` and ``unset``) except for ``get``. Now, output from ``get`` (notably
the ``path`` key) should be piped into other commands. ``onyo set`` and ``onyo
unset`` have renamed ``--path`` to ``--asset`` to accept a list of assets to
operate on.

Meanwhile, ``onyo get``'s filtering has been improved. ``--filter`` is now
renamed ``--match`` and supports Python regular expressions.

Directories can be included or excluded with ``--include`` or ``--exclude``.

Output can be sorted with the ``--sort-ascending`` and ``--sort-descending``
flags. Output can be sorted by multiple keys. Matching and sorting can be
performed on keys that are not included in the output.


Tab Completion
--------------

Tab completion help text is now greatly improved. It has been reduced from
paragraphs of help text (which was of little use and could even break the shell
at times) to terse, useful summaries.

Mutually exclusive flags are no longer suggested.

Many assorted bugs fixed with ``onyo --onyopath`` and spaces in the repo path.


Documentation
-------------

Significant improvements have been made to the help text content, layout, and
highlighting.

Docstrings now use the NumPy format and have seen much improvement. More work is
to come in future releases.

ReadTheDocs now renders docstrings for the Python API.

Other content in ReadTheDocs has received some small cleanup and improvements,
but comparatively less than help text and docstrings. Major improvements will
come in a later release.


Installation
------------
The Python version required by Onyo is bumped from 3.9 to 3.11.

The dependency on ``tree`` has been dropped.


Authors
-------
-  Ben Poldrack (`@bpoldrack <https://github.com/bpoldrack>`__)
-  Alex Waite (`@aqw <https://github.com/aqw>`__)
-  Tobias Kadelka (`@TobiasKadelka <https://github.com/TobiasKadelka>`__)


0.4.0 (2023.04.17)
******************

With this release the Onyo commands allow to add and find information inside a
repository. The ``get`` command extracts data from assets, and with ``new``,
``set`` and ``unset`` it is easy to manage an inventory.
Many flags (``--keys``, ``--message``, ``--depth``, ``--yes``) and
functionalities across all commands are added or normalized to give a smooth and
predictable user experience.
A `demo repository <https://github.com/psyinfra/onyo-demo>`__ shows how an
inventory created and managed with Onyo looks like.
The code-base and tests use a lot of new features and are uplifted to reflect
current standards across the project.

The highlights are:

New Commands
------------
- add command ``onyo unset``: remove key/value pairs from assets
- add command ``onyo get``: query the onyo repository

Command Changes
---------------
- overhaul of ``onyo new``:
    - expect full asset path and name as an argument, instead of reading
      name fields via TUI
    - allow creation of multiple assets in one call
    - verify validity of asset name
    - do not open new assets with an editor by default
    - add diff-like output after reading/combining all information
    - add flags:
        - ``--edit``: open new asset(s) in editor
        - ``--keys``: set key/value(s) to new asset(s)
        - ``--path``: list paths for newly created asset(s)
        - ``--tsv``: read information from table instead of TUI
        - ``--yes``: answer yes to all prompts
- normalize flags ``--path`` and ``--keys`` for commands ``get``, ``new``,
  ``set``, ``unset``
- add ``onyo set --rename``: allows renaming assets (update pseudo-keys), which
  was formerly done with ``onyo mv --rename``
- add ``--message`` flag to all committing commands
- add to ``onyo edit`` flags ``--yes`` and ``--quiet``
- add to ``onyo mkdir`` flags ``--yes`` and ``--quiet``
- remove flag ``onyo set --recursive`` (set and unset operate recursively by
  default)
- key/value pairs are now space-separated (rather than comma-separated)
- normalize user-facing texts ("Update assets? (y/n)") and behavior (remove
  default options, the user has to explicitly answer) across commands
- rename template "standard" -> "empty"
- retire ``.onyo/temp/``, assets are changed in place and changes reverted when
  needed

API
---
- add property ``Repo.templates``: the templates in ``.onyo/`templates``
- remove unused property ``Repo.gitfiles``
- the following public methods are added to ``Repo``:
    - ``validate_name_scheme()``: test that an asset name matches the
      asset name scheme
    - ``get_template()``: return a template path
    - ``clean_caches()``: reset properties of ``Repo``
    - ``restore()``: restore uncommitted changes
    - ``generate_commit_message()``: build the most explicit commit message
      which fits into the character limit with information about the command
      used and assets and directories changed
- add ``fsck`` check for pseudo-key names in asset file(s)
- add doc strings to properties

Bugs
----
- clear caches of properties after modifying the repository to remove stale
  information
- allow special characters in asset and directory names
- order files/dirs in commit messages alphabetically
- enable shell completion when using multiple arguments for the same flag
- tab completion stops listing short/long flag names when the other version was
  already used (e.g. ``--yes`` and ``-y``)
- ``onyo tree`` displays just paths in an onyo repository instead of allowing
  paths to lead outside of the repository
- fix "tests badge"

Docs
----
- add "Code Conventions" to readme
- add badge for demo deploy status

Tests
-----
- run tests in random order
- add fixture ``repo_contents`` for setting asset contents
- add/expand tests for changed behavior of ``onyo new``
- add tests for ``onyo unset``
- add tests for ``onyo tree``
- add tests for ``Repo.valid_name()``
- expand tests for ``onyo set``
- modernize/normalize all tests under ``tests/``
    - fixtures, doc-strings, parameterization, type hints
    - add special character tests
    - test single/list of path arguments as input
- remove ``test_invoking.py`` and ``reference_output/``

Demo
----
- add ``demo.sh``
    - runs a list of commands to create an example repository
    - deploy example repository at https://github.com/psyinfra/onyo-demo
- add demo information to docs and readme

Authors
-------
- Tobias Kadelka (`@TobiasKadelka <https://github.com/TobiasKadelka>`__)
- Alex Waite (`@aqw <https://github.com/aqw>`__)
- Niels Reuter (`@nhjjr <https://github.com/nhjjr>`__)

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
