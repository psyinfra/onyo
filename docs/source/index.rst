Welcome to Onyo's documentation!
================================

Onyo is a text-based inventory system backed by git. There is no server, SQL
database, web interface, etc. It is inspired by `pass`_ (password management) and
`ledger`_ (of `plain text accounting`_ fame).

Onyo uses the filesystem as the index and git to track history. This allows much
of Onyo's functionality to be just a thin wrapper around git commands.

Overview
********

.. toctree::
   :maxdepth: 1

   installation
   concepts
   command_line_reference
   examples

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _pass: https://www.passwordstore.org
.. _ledger: https://www.ledger-cli.org
.. _plain text accounting: https://plaintextaccounting.org
