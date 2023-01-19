import logging
import sys

from onyo import Repo, OnyoInvalidRepoError
from onyo.commands.edit import request_user_response

logging.basicConfig()
log = logging.getLogger('onyo')


def set(args, opdir: str) -> None:
    """
    Set the ``value`` of ``key`` for matching assets. If the key does not exist,
    it is added and set appropriately.

    Key names can be any valid YAML key name.

    Multiple ``key=value`` pairs can be declared and divided by spaces. Quotes
    can be used around ``value``, which is necessary when it contains a comma,
    whitespace, etc.

    The ``type``, ``make``, ``model``, and ``serial`` pseudo-keys can be set
    when the `--rename` flag is used. It will result in the file(s) being
    renamed.

    If no ``asset`` or ``directory`` is specified, the current working directory
    is used. If Onyo is invoked from outside of the Onyo repository, the root of
    the repository is used.

    Changes are printed to the terminal in the style of ``diff``.

    Errors reading or parsing files print to STDERR, but do not halt Onyo. Any
    error encountered while writing a file will cause Onyo to error and exit
    immediately.
    """
    repo = None

    # check flags for conflicts
    if args.quiet and not args.yes:
        print('The --quiet flag requires --yes.', file=sys.stderr)
        sys.exit(1)

    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    diff = ""
    try:
        diff = repo.set(args.path, args.keys, args.dry_run, args.rename, args.depth)
    except ValueError:
        sys.exit(1)

    # display changes
    if not args.quiet and diff:
        print("The following assets will be changed:")
        print(diff)
    elif args.quiet:
        pass
    else:
        print("The values are already set. No assets updated.")
        sys.exit(0)

    # commit or discard changes
    files_staged = repo.files_staged
    if files_staged:
        if args.yes or request_user_response("Update assets? (y/n) "):
            repo.commit('set values', files_staged)
        else:
            repo._git(['restore', '--source=HEAD', '--staged', '--worktree'] + [str(file) for file in files_staged])
            # when names were changed, the first restoring just brings
            # back the name, but leaves working-tree unclean
            files_staged = repo.files_staged
            if files_staged:
                repo._git(['restore', '--source=HEAD', '--staged', '--worktree'] + [str(file) for file in files_staged])
            if not args.quiet:
                print("No assets updated.")
