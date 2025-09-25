from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.commands import onyo_tsv_to_yaml


if TYPE_CHECKING:
    import argparse

args_tsv_to_yaml = {
    'tsv': dict(
        metavar='TSV',
        nargs=1,
        help=r"""
            Path of tabular file to convert to YAML.
        """
    ),
}

epilog_tsv_to_yaml = r"""
.. rubric:: Examples

print a table's contents in the YAML format:

.. code:: shell

    $ onyo tsv-to-yaml table.tsv

Split the resulting multi-document YAML output into separate YAML documents:

.. code:: shell

    $ onyo tsv-to-yaml table.tsv | csplit -z --suffix-format '%04d.yaml' - "/---/" "{*}"
"""


def tsv_to_yaml(args: argparse.Namespace) -> None:
    r"""
    Print a TSV file's contents as YAML, suitable to pass into ``onyo new`` and ``onyo set``.

    The output is printed to stdout as a multi-document YAML file, and each
    document is separated with a ``---`` line.

    The TSV file's header row declares the key names for all resulting YAML
    documents, and each row of the table declares the values for one of the
    YAML documents.
    """

    onyo_tsv_to_yaml(tsv=Path(args.tsv[0]).resolve())
