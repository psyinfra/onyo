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

.. code:: shell

    $ onyo tsv-to-yaml table.tsv

The resulting multi-document YAML file can be split into multiple YAML files (if
desired) using ``csplit``.

.. code:: shell

    $ onyo tsv-to-yaml table.tsv | csplit -z --suffix-format '%04d.yaml' - "/---/" "{*}"
"""


def tsv_to_yaml(args: argparse.Namespace) -> None:
    r"""
    Convert a tabular file (e.g. TSV, CSV) to YAML suitable for passing to
    ``onyo new`` and ``onyo set``.

    The header declares the key names to be populated. The values to populate
    documents are declared with one line per YAML document.

    The output is printed to stdout as a multiple document YAML file (each
    document is separated by a ``---`` line).
    """

    onyo_tsv_to_yaml(tsv=Path(args.tsv[0]).resolve())
