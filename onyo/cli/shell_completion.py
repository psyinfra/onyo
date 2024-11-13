from __future__ import annotations

from importlib import resources
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

args_shell_completion = {
    'shell': dict(
        args=('-s', '--shell'),
        metavar='SHELL',
        required=False,
        default='zsh',
        choices=['zsh'],
        help=r"""
            The shell to generate a tab-completion script for.
        """
    )
}

epilog_shell_completion = r"""
.. rubric:: Examples

Enable shell completion for ``onyo``:

.. code:: shell

    $ source <(onyo shell-completion)
    $ onyo --<press TAB to display available options>
"""


def shell_completion(args: argparse.Namespace) -> None:
    r"""
    Display a tab-completion shell script for Onyo.

    The output of this command is suitable to ``source`` in your shell.
    """
    print(resources.files('onyo.shell_completion').joinpath(args.shell).read_text())
