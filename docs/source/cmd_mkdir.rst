onyo mkdir
==========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: mkdir

Example Usage
*************

**Add a new user to a group**

.. code:: shell

    onyo mkdir accounting/Bingo\ Bob/


**Create a new group with some users**

.. code:: shell

    onyo mkdir --message "the marketing group joined\!" marketing/Alice\ Wonder/ marketing/Karl\ Krebs
