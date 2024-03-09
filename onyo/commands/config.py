from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo import OnyoRepo
from onyo.argparse_helpers import git_config
from onyo.lib.commands import onyo_config
from onyo.lib.inventory import Inventory

if TYPE_CHECKING:
    import argparse

args_config = {
    'git_config_args': dict(
        metavar='ARGS',
        nargs='+',
        type=git_config,
        help='Config options to set in .onyo/config'
    ),
}


def config(args: argparse.Namespace) -> None:
    """
    Set, query, and unset Onyo repository configuration options.

    These options are stored in ``.onyo/config``, which is tracked by git and
    shared with all other users of the Onyo repository.

    To set configuration options locally (and not commit them to the Onyo
    repository), use ``git config`` instead.

    ``onyo config`` is a wrapper around ``git config``. All of its options and
    capabilities are available with the exception of ``--system``, ``--global``,
    ``--local``, ``--worktree``, and ``--file``. Please see the git-config
    manpage for more information about usage.

    Onyo configuration options:

        * ``onyo.assets.filename``: The format for asset names on the
          filesystem. (default: "{type}_{make}_{model}.{serial}")
        * ``onyo.core.editor``: The editor to use for commands such as ``edit``
          and ``new``. If unset, it will fallback to the environmental variable
          ``EDITOR`` and lastly ``nano``. (default: unset)
        * ``onyo.history.interactive``: The interactive command to use for
          ``onyo history``. (default: "tig --follow")
        * ``onyo.history.non-interactive``: The non-interactive command for
          running ``onyo history --non-interactive``.
          (default: "git --no-pager log --follow")
        * ``onyo.new.template``: The default template to use with ``onyo new``.
          (default: "empty")
        * ``onyo.repo.version``: The Onyo repository version.
    """

    # TODO: Wouldn't we want to commit (implying message parameter)?

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_config(inventory,
                args.git_config_args)
