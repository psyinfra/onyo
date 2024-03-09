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
        help="""
            The shell to generate a tab-completion script for.
        """
    )
}


def shell_completion(args: argparse.Namespace) -> None:
    """
    Display a tab-completion shell script for Onyo.

    The output of this command should be "sourced" to enable tab completion.

    Example:

        ```
        source <(onyo shell-completion)
        onyo --<PRESS TAB to display available options>
        ```
    """
    content = ''
    shell_completion_dir = Path(__file__).resolve().parent.parent / 'shell_completion'

    if args.shell == 'zsh':
        shell_completion_file = shell_completion_dir / 'zsh' / '_onyo'

    # TODO: add bash
    # bash: ~/.local/share/bash-completion/completions

    content = shell_completion_file.read_text()
    print(content)
