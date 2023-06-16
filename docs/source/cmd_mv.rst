onyo mv
=======

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: mv

Example Usage
*************

**Assign an asset**

.. code:: shell

   onyo mv shelf/laptop_lenovo_T490s.abc123 accounting/Bingo\ Bob/

**Retire an asset**

.. code:: shell

   onyo mv accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123 retired/

**Move a user to another workgroup**

.. code:: shell

   onyo mv --message "Bob is now an admin!" accounting/Bingo\ Bob/ admin/

**Rename a group**

.. code:: shell

   onyo mv --message "Marketing is now Advertisement" marketing/ advertisement/
