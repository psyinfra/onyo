onyo config
===========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: config


Example Usage
*************

**Update the default tools for onyo history**

.. code:: shell

    onyo config onyo.history.interactive "tig –follow"
    onyo config onyo.history.non-interactive "git –no-pager log –follow"

**Change the default template used by onyo new**

.. code:: shell

    onyo config onyo.new.template "laptop.example"

**Change the editor used by onyo new and onyo edit**

.. code:: shell

    onyo config onyo.core.editor vim
