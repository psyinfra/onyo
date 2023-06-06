onyo set
========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: set

Example Usage
*************

**Upgrade an asset**

.. code:: shell

   onyo set --keys RAM=16GB --path accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123
   - RAM: 8GB
   + RAM: 16GB
