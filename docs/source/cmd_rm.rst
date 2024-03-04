onyo rm
=======

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: rm


Example Usage
*************

**Delete an asset from the inventory**

.. code:: shell

    onyo rm shelf/laptop_lenovo_T490s.abc123

**Retire a user**

.. code:: shell

    onyo rm --message "Bob retired" admin/Bingo\ Bob/
