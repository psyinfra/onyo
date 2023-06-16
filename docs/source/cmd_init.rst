onyo init
=========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: init

Example Usage
*************

**Set up the current working directory as an onyo repository**

.. code:: shell

   onyo init

**Initialize an existing directory as an onyo repository**

.. code:: shell

    onyo init my_inventory

or

.. code:: shell

    onyo init /abs/path/my_inventory

**Create a new directory and set it up as an onyo repository**

.. code:: shell

   onyo init new_inventory_directory
