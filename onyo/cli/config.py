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

    These options are stored in ``.onyo/config``, which is tracked by git and
    shared with all other users of the Onyo repository.

    To set configuration options locally (and not commit them to the Onyo
    repository), use ``git config`` instead.

    This command is a wrapper around ``git config``. All of its options and
    capabilities are available with the exception of ``--system``, ``--global``,
    ``--local``, ``--worktree``, and ``--file``. Please see the **git-config**
    manpage for more information about usage.

    Onyo configuration options:

      * ``onyo.assets.name-format``: The format for asset names on the
        filesystem. (default: "{type}_{make}_{model}.{serial}")
      * ``onyo.core.editor``: The editor to use for subcommands such as ``edit``
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
