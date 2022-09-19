Changelog
=========

Next
****

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
