onyo new
========

.. argparse::
   :module: onyo.main
   :func: setup_parser
   :prog: onyo
   :path: new


Reserved keys
*************

Onyo reserves some keys which have a special function when used while creating
new assets, either with ``onyo new --keys`` or in templates.

They can be used multiple times with different values to create multiple
new assets at once with a different value for each asset.

**directory**

    The ``directory`` key is an alternative to ``onyo new --directory`` to specify
    the location in which to create new assets.

**template**

    The ``template`` key is an alternative to ``onyo new --template`` to specify
    which template to use to create new assets.
