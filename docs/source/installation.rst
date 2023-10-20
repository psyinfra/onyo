Installation
============

Non-Python Dependencies
***********************

In addition to Python >= 3.11 and a few Python modules, Onyo depends on a few
system utilities.

**Debian/Ubuntu**:

.. code:: shell

   apt-get install git tig tree

**macOS**:

.. code:: shell

   brew install git tig tree


Onyo
****

To install Onyo, run the following from your command line:

.. code::

   pip install git+https://github.com/psyinfra/onyo.git


.. _aliases:

Aliases
*******

If you have an Onyo repository and you want to be able to operate on it from
anywhere on the system, set an alias passing ``-C``. For example, for Bourne
shells:

.. code::

   alias onyo='onyo -C path/to/repo'

Or for multiple repos:

.. code::

   alias onyo-home='onyo -C path/to/home.repo'
   alias onyo-corp='onyo -C path/to/corp.repo'

The same technique can be used to invoke ``git`` on an Onyo repo from anywhere
on the system:

.. code::

   alias onyo-git='git -C path/to/repo'

Add aliases to your shell's config file (e.g. ``~/.bashrc`` or ``~/.zshrc``) to
make them persistent.
