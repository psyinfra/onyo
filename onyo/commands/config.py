#!/usr/bin/env python3

import logging
import os
import subprocess
import sys
from git import Repo
from onyo.commands.fsck import read_only_fsck

logging.basicConfig()
logger = logging.getLogger('onyo')


def sanitize_args(git_config_args):
    """
    Check the git config arguments against a list of conflicting options. If
    conflicts are present, the conflict list will be printed and will exit with
    error.

    Returns the unmodified  git config args on success.
    """
    # git-config supports multiple layers of git configuration. Onyo uses
    # ``--file`` to write to .onyo/config. Other options are excluded.
    forbidden_flags = ['--system',
                       '--global',
                       '--local',
                       '--worktree',
                       '--file',
                       '--blob',
                       '--help',
                       '-h',
                       ]

    for a in git_config_args:
        if a in forbidden_flags:
            logger.error("The following options cannot be used with onyo config:")
            logger.error('\n'.join(forbidden_flags))
            logger.error("\nExiting. Nothing was set.")
            sys.exit(1)

    return git_config_args


def config(args, onyo_root):
    """
    Set, query, and unset Onyo repository configuration options. These options
    are stored in ``.onyo/config`` (which is tracked by git) and are shared with
    all other consumers of an Onyo repository.

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
      (default: "standard")

    Example:

        $ onyo config onyo.core.editor "vim"
    """
    read_only_fsck(args, onyo_root, quiet=True)

    git_config_args = sanitize_args(args.git_config_args)
    repo = Repo(onyo_root)
    # TODO: because onyo_root is not actually the root of the onyo repo
    repo_root = repo.git.rev_parse('--show-toplevel')

    # NOTE: streaming stdout and stderr directly to the terminal seems to be
    # non-trivial with "subprocess". Here we capture them separately. They
    # won't be interwoven, but will be output to the correct destinations.
    ret = subprocess.run(["git", 'config', '-f', '.onyo/config'] + git_config_args,
                         cwd=repo_root, capture_output=True, text=True)

    # print any output gathered
    if ret.stdout:
        print(ret.stdout, end='')
    if ret.stderr:
        print(ret.stderr, file=sys.stderr, end='')

    # bubble up error retval
    if ret.returncode != 0:
        exit(ret.returncode)

    # commit, if there's anything to commit
    if repo.is_dirty():
        dot_onyo_config = os.path.join(repo_root, '.onyo/config')
        repo.git.add(dot_onyo_config)
        repo.git.commit(m='onyo config: modify shared repository config')
