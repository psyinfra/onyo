Installation
============

Setup and activate virtual environment
**************************************

With your virtual environment manager of choice, create a virtual environment
and ensure you have a recent version of Python installed. Then activate the
environment. E.g. with ``venv``:

.. code::

   python -m venv ~/.venvs/onyo
   source ~/.venvs/onyo/bin/activate

Clone the repo and install the package
**************************************

Run the following from your command line:

.. code::

   git clone https://github.com/psyinfra/onyo.git
   cd onyo
   pip install -e .

Install Dependencies
********************

Additional non-python dependencies need to be installed:

**Debian/Ubuntu**:

.. code:: shell

   apt-get install git tig tree

**macOS**:

.. code:: shell

   brew install git tig tree
