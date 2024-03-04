onyo cat
========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: cat

Example Usage
*************

**Display the contents of an asset file**


.. code:: shell

    onyo cat accounting/Bingo\ Bob/laptop_lenovo_T490s.abc123

    type: laptop
    make: lenovo
    model: T490s
    serial: abc123
    RAM: 16GB
    display_size: '14.6'
    touch: yes
