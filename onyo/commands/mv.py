import sys
from pathlib import Path

from onyo.lib import Repo, OnyoInvalidRepoError, OnyoProtectedPathError


def mv(args, opdir: str) -> None:
    """
    Move ``source``\(s) (assets or directories) to the ``destination``
    directory, or rename a ``source`` directory to ``destination``.

    Files cannot be renamed using ``onyo mv``. To do so, use ``onyo set``.
    """
    repo = None

    # check flags
    if args.quiet and not args.yes:
        print('The --quiet flag requires --yes.', file=sys.stderr)
        sys.exit(1)

    try:
        repo = Repo(opdir)
        repo.fsck()
    except OnyoInvalidRepoError:
        sys.exit(1)

    if not args.quiet:
        dryrun_list = None
        try:
            dryrun_list = repo.mv(args.source, args.destination, dryrun=True)
        except (FileExistsError, FileNotFoundError, NotADirectoryError, OnyoProtectedPathError, ValueError):
            sys.exit(1)

        print('The following will be moved:\n' +
              '\n'.join(f"'{x[0]}' -> '{x[1]}'" for x in dryrun_list))

        if not args.yes:
            response = input('Move assets? (y/N) ')
            if response not in ['y', 'Y', 'yes']:
                print('Nothing was moved.')
                sys.exit(0)

    try:
        repo.mv(args.source, args.destination)
        repo.commit('mv: ' +
                    ','.join(["'{}'".format(Path(opdir, x).resolve().relative_to(repo.root)) for x in args.source]) +
                    ' -> ' + str(Path(opdir, args.destination).resolve().relative_to(repo.root)))
    except (FileExistsError, FileNotFoundError, OnyoProtectedPathError, ValueError):
        sys.exit(1)
