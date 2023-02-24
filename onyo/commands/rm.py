import sys

from onyo import Repo, OnyoInvalidRepoError, OnyoProtectedPathError


def rm(args, opdir: str) -> None:
    """
    Delete ``asset``\(s) and ``directory``\(s).

    A list of all files and directories to delete will be presented, and the
    user prompted for confirmation.
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
            dryrun_list = repo.rm(args.path, dryrun=True)
        except (FileNotFoundError, OnyoProtectedPathError):
            sys.exit(1)

        print('The following will be deleted:\n' +
              '\n'.join(dryrun_list))

        if not args.yes:
            response = input('Delete assets? (y/N) ')
            if response not in ['y', 'Y', 'yes']:
                print('Nothing was deleted.')
                sys.exit(0)

    try:
        repo.rm(args.path)
        repo.commit(repo.generate_commit_message(message=args.message,
                                                 cmd="rm"))
    except (FileNotFoundError, OnyoProtectedPathError):
        sys.exit(1)
