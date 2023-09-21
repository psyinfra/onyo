from __future__ import annotations
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.lib.commands import config as config_cmd, fsck
from onyo.argparse_helpers import git_config

if TYPE_CHECKING:
    import argparse

logging.basicConfig()
log: logging.Logger = logging.getLogger('onyo')

args_config = {
    'git_config_args': dict(
        metavar='ARGS',
        nargs='+',
        type=git_config,
        help='Config options to set in .onyo/config'),
}


def config(args: argparse.Namespace) -> None:
    """
    Set, query, and unset Onyo repository configuration options. These options
    are stored in ``.onyo/config``. This file is tracked by git and are shared
    with all other consumers of an Onyo repository.

    To set configuration options locally (and not commit them to the Onyo
    repository), use ``git config`` instead.

    ``onyo config`` is a wrapper around ``git config``. All of its options and
    capabilities are available with the exception of ``--system``, ``--global``,
    ``--local``, ``--worktree``, and ``--file``. Please see the git-config
    manpage for more information about usage.

    Onyo configuration options:

    - ``onyo.core.editor``: The editor to use for commands such as ``edit`` and
      ``new``. If unset, it will fallback to the environmental variable
      ``EDITOR`` and lastly ``nano``. (default: unset)
    - ``onyo.history.interactive``: The command used to display history when
      running ``onyo history``. (default: "tig --follow")
    - ``onyo.history.non-interactive``: The command used to print history when
      running ``onyo history`` with ``--non-interactive``.
      (default: "git --no-pager log --follow")
    - ``onyo.new.template``: The default template to use with ``onyo new``.
      (default: "empty")
    """

    repo = OnyoRepo(Path.cwd(), find_root=True)
    fsck(repo, ['asset-yaml'])
    config_cmd(repo, args.git_config_args)
