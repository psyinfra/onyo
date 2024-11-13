from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.onyo import OnyoRepo
from onyo.lib.commands import onyo_config
from onyo.lib.inventory import Inventory

if TYPE_CHECKING:
    import argparse

args_config = {
    'git_config_args': dict(
        metavar='ARGS',
        nargs='+',
        help=r"""
            Configuration arguments to operate on ``.onyo/config``.
        """
    ),
}

epilog_config = r"""
.. rubric:: Configuration Options

``onyo.assets.name-format``:
  The format for asset names on the filesystem.
  Default: "{type}_{make}_{model}.{serial}"

``onyo.core.editor``:
  The command to run subcommands such as ``edit`` and ``new --edit``. If unset,
  it will fallback to ``git``'s ``core.editor``, then the environmental variable
  ``EDITOR``, and lastly ``nano``.
  Default: unset

``onyo.history.interactive``:
  The command to run for ``onyo history``.
  Default: "tig --follow"

``onyo.history.non-interactive``:
  The command to run for ``onyo history --non-interactive``.
  Default: "git --no-pager log --follow"

``onyo.new.template``:
  The default template to use with ``onyo new``.
  Default: "empty"

``onyo.repo.version``:
  The Onyo repository version.

.. rubric:: Examples

Get the tool used for interactive history:

.. code:: shell

    $ onyo config --get onyo.history.interactive

Set the default template used by ``onyo new``:

.. code:: shell

    $ onyo config onyo.new.template "generic.asset"
"""


def config(args: argparse.Namespace) -> None:
    r"""
    Set, query, and unset Onyo repository configuration options.

    These options are stored in ``.onyo/config``, which is in the Onyo
    repository and thus shared with all other consumers of the repository.

    To set configuration options locally (and not commit them to the Onyo
    repository), use ``git config`` instead.

    This command is a wrapper around ``git config``. All of its options and
    capabilities are available with the exception of ``--system``, ``--global``,
    ``--local``, ``--worktree``, and ``--file``. Please see the **git-config**
    manpage for more information about usage.
    """

    # Though this commit makes changes and commits, the --message and
    # --no-auto-message flags are omitted to simplify passing args to
    # git-config.
    # A motivated individual could choose to fix this.

    inventory = Inventory(repo=OnyoRepo(Path.cwd(), find_root=True))
    onyo_config(inventory,
                args.git_config_args)
