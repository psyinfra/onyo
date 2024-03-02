from __future__ import annotations

from pathlib import Path
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
        help='Specify the shell for which to generate tab completion for')
}


def shell_completion(args: argparse.Namespace) -> None:
    """
    Display a shell script for tab completion for Onyo.

    The output of this command should be "sourced" to enable tab completion.

    example:

        $ source <(onyo shell-completion)
        $ onyo --<PRESS TAB to display available options>
    """
    content = ''
    shell_completion_dir = Path(__file__).resolve().parent.parent / 'shell_completion'

    if args.shell == 'zsh':
        shell_completion_file = shell_completion_dir / 'zsh' / '_onyo'

    # TODO: add bash

    content = shell_completion_file.read_text()
    print(content)
