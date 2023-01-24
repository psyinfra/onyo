Welcome to Onyo's documentation!
================================

Onyo is a text-based inventory system backed by git. There is no server, SQL
database, web interface, etc. It is inspired by `pass`_ (password management) and
`ledger`_ (of `plain text accounting`_ fame).

Onyo uses the filesystem as the index and git to track history. This allows much
of Onyo's functionality to be just a thin wrapper around git commands.

An `example Onyo repository`_ is available. It's easier to get a feel for how
Onyo works with a populated repository with actual history, rather than starting
from scratch. Just install Onyo, clone the demo repo, and start poking around!

Overview
********

.. toctree::
   :maxdepth: 1

   installation
   configuration
   concepts
   command_line_reference
   examples
   changelog

.. _pass: https://www.passwordstore.org
.. _ledger: https://www.ledger-cli.org
.. _plain text accounting: https://plaintextaccounting.org
.. _example Onyo repository: https://github.com/psyinfra/onyo-demo/
