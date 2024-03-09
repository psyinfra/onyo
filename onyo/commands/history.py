from __future__ import annotations

import os
import sys
from pathlib import Path
from shlex import quote
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import path
from onyo.lib.command_utils import get_history_cmd
from onyo.lib.ui import ui

if TYPE_CHECKING:
    import argparse

args_history = {
    'interactive': dict(
        args=('-I', '--non-interactive'),
        required=False,
        default=True,
        action='store_false',
        help="""
            Use the non-interactive tool to display history.
        """
    ),

    'path': dict(
        metavar='PATH',
        nargs='?',
        type=path,
        help="""
            PATH of an asset or directory to display the history of.
        """
    ),
}


def history(args: argparse.Namespace) -> None:
    """
    Display the history of ``PATH``.

    Onyo makes an effort to detect if the TTY is interactive in order to
    automatically select whether to use the interactive or non-interactive
    history tool.

    The commands to display history are configurable using ``onyo config``:

        * ``onyo.history.interactive``
        * ``onyo.history.non-interactive``
    """

    # Note: Currently exceptional command in that it's not a function in lib/commands, because of exit code handling.
    #       Need to enhance error handling in main.py first.

    # TODO: Not sure about args.path not given. Doesn't necessarily work with any all history commands.

    repo = OnyoRepo(Path.cwd(), find_root=True)

    # get the command and path
    path = Path(args.path).resolve() if args.path else Path.cwd()

    # check if path exists
    # Note: This is a strange criterion. Can you "display the history" of a file whenever it exists?
    #       No. What's relevant is whether it's tracked in git. However, why check upfront at all? We fail, if the
    #       history cmd fails. Whatever history command one is using it needs to figure that same thing out again one
    #       way or another. Nothing gained here.
    if path and not path.exists():
        ui.error(f"Cannot display the history of '{path}'. It does not exist.")
        ui.error("Exiting.")
        sys.exit(1)

    history_cmd = get_history_cmd(args.interactive, repo)

    # run it
    status = 0
    try:
        status = os.system(f"{history_cmd} {quote(str(path if path else repo.git.root))}")
    except:  # noqa: E722
        pass

    # covert the return status into a return code
    returncode = os.waitstatus_to_exitcode(status)

    # bubble up error retval
    if returncode != 0:
        sys.exit(returncode)
