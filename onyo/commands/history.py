from __future__ import annotations
import os
import sys
from pathlib import Path
from shlex import quote
from typing import TYPE_CHECKING

from onyo import OnyoRepo, ui
from onyo.lib.command_utils import get_history_cmd
from onyo.lib.commands import fsck
from onyo.argparse_helpers import path

if TYPE_CHECKING:
    import argparse

args_history = {
    'interactive': dict(
        args=('-I', '--non-interactive'),
        required=False,
        default=True,
        action='store_false',
        help=(
            "Use the interactive history tool (specified in '.onyo/config' "
            "under 'onyo.history.interactive') to display the history of the "
            "repository, an asset or a directory")),

    'path': dict(
        metavar='PATH',
        nargs='?',
        type=path,
        help='Specify an asset or a directory to show the history of'),
}


def history(args: argparse.Namespace) -> None:
    """
    Display the history of an ``ASSET`` or ``DIRECTORY``.

    Onyo detects whether an interactive TTY is in use, and will either use
    the interactive display tool (specified in ``.onyo/config`` under
    ``onyo.history.interactive``; default ``tig –-follow``) or the
    non-interactive one (``onyo.history.non-interactive``; default ``git log``)
    accordingly.

    The commands to display history are configurable using ``onyo config``.
    """

    # Note: Currently exceptional command in that it's not a function in lib/commands, because of exit code handling.
    #       Need to enhance error handling in main.py first.

    # TODO: Not sure about args.path not given. Doesn't necessarily work with any all history commands.

    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo, ['asset-yaml'])

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
