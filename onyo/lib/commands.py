from __future__ import annotations

import subprocess
import sys
import logging
from typing import Optional, Union, Iterable, Dict
from pathlib import Path

from rich.console import Console
from rich import box
from rich.table import Table

from onyo.lib.assets import PSEUDO_KEYS, get_assets_by_query
from onyo.lib.command_utils import get_editor, edit_asset, request_user_response, sanitize_keys, set_filters, \
    fill_unset, natural_sort, validate_args_for_new, onyo_mv
from onyo.lib.exceptions import OnyoInvalidRepoError
from onyo.lib.filters import UNSET_VALUE
from onyo.lib.onyo import OnyoRepo


log: logging.Logger = logging.getLogger('onyo.commands')


def fsck(repo: OnyoRepo, tests: Optional[list[str]] = None) -> None:
    """
    Run a suite of checks to verify the integrity and validity of an Onyo
    repository and its contents.

    By default, the following tests will be performed:

    - "clean-tree": verifies that the git tree is clean ---that there are
      no changed (staged or unstaged) nor untracked files.
    - "anchors": verifies that all folders (outside of .onyo) have an
      .anchor file
    - "asset-unique": verifies that all asset names are unique
    - "asset-yaml": loads each assets and checks if it's valid YAML
    - "asset-validity": loads each asset and validates the contents against
      the validation rulesets defined in ``.onyo/validation/``.
    - "pseudo-keys": verifies that assets do not contain pseudo-key names
    """

    from functools import partial
    from .assets import has_unique_names, validate_yaml, validate_assets, contains_no_pseudo_keys

    all_tests = {
        "clean-tree": repo.git.is_clean_worktree,
        "anchors": repo.validate_anchors,
        "asset-unique": partial(has_unique_names, repo.asset_paths),
        "asset-yaml": partial(validate_yaml, {repo.git.root / a for a in repo.asset_paths}),
        "asset-validity": partial(validate_assets, repo.asset_paths),
        "pseudo-keys": partial(contains_no_pseudo_keys, repo.asset_paths)
    }
    if tests:
        # only known tests are accepted
        if [x for x in tests if x not in all_tests.keys()]:
            raise ValueError("Invalid test requested. Valid tests are: {}".format(', '.join(all_tests.keys())))
    else:
        tests = list(all_tests.keys())

    # run the selected tests
    for key in tests:
        # TODO: these should be INFO
        log.debug(f"'{key}' starting")

        if not all_tests[key]():
            # Note: Why report on opdir rather than root? The repository failed the tests, not a subtree
            #       Also: What's that debug message adding? Alone it lacks the identifying path and in combination with
            #       the exception it's redundant.
            log.debug(f"'{key}' failed")
            raise OnyoInvalidRepoError(f"'{repo.git.root}' failed fsck test '{key}'")

        log.debug(f"'{key}' succeeded")


def cat(repo: OnyoRepo, paths: Iterable[Path]) -> None:

    non_asset_paths = [str(p) for p in paths if not repo.is_asset_path(p)]
    if non_asset_paths:
        raise ValueError("The following paths are not asset files:\n%s",
                         "\n".join(non_asset_paths))
    # open file and print to stdout
    for path in paths:
        print(path.read_text(), end='')


def config(repo: OnyoRepo, config_args: list[str]) -> None:

    from onyo.lib.command_utils import sanitize_args_config
    git_config_args = sanitize_args_config(config_args)

    config_file = repo.dot_onyo / 'config'
    # NOTE: streaming stdout and stderr directly to the terminal seems to be
    # non-trivial with "subprocess". Here we capture them separately. They
    # won't be interwoven, but will be output to the correct destinations.
    ret = subprocess.run(["git", 'config', '-f', str(config_file)] + git_config_args,
                         cwd=repo.git.root, capture_output=True, text=True)

    # print any output gathered
    if ret.stdout:
        print(ret.stdout, end='')
    if ret.stderr:
        print(ret.stderr, file=sys.stderr, end='')

    # bubble up error retval
    if ret.returncode != 0:
        exit(ret.returncode)

    # commit, if there's anything to commit
    if repo.git.files_changed:
        repo.git.stage_and_commit(config_file, 'config: modify repository config')


def edit(repo: OnyoRepo,
         asset_paths: Iterable[Path],
         message: list[str],
         quiet: bool,
         yes: bool) -> None:
    # check flags for conflicts
    if quiet and not yes:
        raise ValueError('The --quiet flag requires --yes.')

    # "onyo fsck" is intentionally not run here.
    # This is so "onyo edit" can be used to fix an existing problem. This has
    # benefits over just simply using `vim`, etc directly, as "onyo edit" will
    # validate the contents of the file before saving and committing.

    # check and set paths
    # Note: This command is an exception. It skips the invalid paths and proceeds to act upon the valid ones!
    valid_asset_paths = []
    for a in asset_paths:
        if not repo.is_asset_path(a):
            print(f"\n{a} is not an asset.", file=sys.stderr)
        else:
            valid_asset_paths.append(a)
    if not valid_asset_paths:
        raise RuntimeError("No asset updated.")

    editor = get_editor(repo)

    for asset in valid_asset_paths:
        if edit_asset(editor, asset):
            repo.git.add(asset)
        else:
            # If user wants to discard changes, restore the asset's state
            repo.git._git(['restore', str(asset)])
            if not quiet:
                print(f"'{asset}' not updated.")

    # commit changes
    staged = sorted(repo.git.files_staged)
    if staged:
        if not quiet:
            print(repo.git._diff_changes())
        if yes or request_user_response("Save changes? No discards all changes. (y/n) "):
            repo.git.commit(repo.generate_commit_message(message=message,
                                                         cmd="edit"))
        else:
            repo.git.restore()
            if not quiet:
                print('No assets updated.')


def get(repo: OnyoRepo,
        sort_ascending: bool,
        sort_descending: bool,
        paths: list[Path],
        depth: int,
        machine_readable: bool,
        filter_strings: list[str],
        keys: list[str]) -> None:

    if sort_ascending and sort_descending:
        msg = (
            '--sort-ascending (-s) and --sort-descending (-S) cannot be used '
            'together')
        if machine_readable:
            print(msg, file=sys.stderr)
        else:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {msg}')
        raise ValueError

    # validate path arguments
    invalid_paths = set(p for p in paths if not repo.is_inventory_dir(p))
    if invalid_paths:
        err_str = '\n'.join([str(x) for x in invalid_paths])
        raise ValueError(f"The following paths do not exist:\n{err_str}")
    if not paths:
        raise ValueError("No assets selected.")
    if depth < 0:
        raise ValueError(f"-d, --depth must be 0 or larger, not '{depth}'")

    keys = sanitize_keys(keys, defaults=PSEUDO_KEYS)
    filters = set_filters(
        filter_strings, repo=repo,
        rich=not machine_readable) if filter_strings else None

    results = get_assets_by_query(
        repo.asset_paths, keys=set(keys), paths=paths, depth=depth, filters=filters)
    results = fill_unset(results, keys, UNSET_VALUE)
    results = natural_sort(
        assets=list(results),
        keys=keys if sort_ascending or sort_descending else None,
        reverse=True if sort_descending else False)

    if machine_readable:
        sep = '\t'  # column separator
        for asset, data in results:
            values = sep.join([str(value) for value in data.values()])
            print(f'{values}{sep}{asset.relative_to(Path.cwd())}')
    else:
        console = Console()
        table = Table(
            box=box.HORIZONTALS, title='', show_header=True,
            header_style='bold')

        for key in keys:
            table.add_column(key, no_wrap=True)

        table.add_column('path', no_wrap=True)

        if results:
            for asset, data in results:
                values = [str(value) for value in data.values()]
                table.add_row(*values, str(asset.relative_to(Path.cwd())))

            console.print(table)
        else:
            console.print('No assets matching the filter(s) were found')


def mkdir(repo: OnyoRepo, dirs: list[Path], quiet: bool, yes: bool, message: Union[list[str], None]) -> None:

    repo.mk_inventory_dirs(dirs)

    # commit changes
    staged = sorted(repo.git.files_staged)
    if not quiet:
        print(
            'The following directories will be created:',
            *map(str, staged), sep='\n')

    if yes or request_user_response(
            "Save changes? No discards all changes. (y/n) "):
        repo.git.commit(repo.generate_commit_message(
            message=message, cmd="mkdir"))
    else:
        repo.git.restore()
        if not quiet:
            print('No assets updated.')


def mv(repo: OnyoRepo,
       source: Union[Iterable[Path], Path],
       destination: Path,
       quiet: bool,
       yes: bool,
       message: Union[list[str], None]) -> None:

    # check flags
    if quiet and not yes:
        raise ValueError("The --quiet flag requires --yes.")

    # Note: Why does the dryrun execution depend on quiet?
    if not quiet:
        dryrun_list = onyo_mv(repo, source, destination, dryrun=True)
        print('The following will be moved:\n' +
              '\n'.join(f"'{x[0]}' -> '{x[1]}'" for x in dryrun_list))

        if not yes and not request_user_response("Save changes? No discards all changes. (y/n) "):
            print('Nothing was moved.')
            return

    onyo_mv(repo, source, destination)
    repo.git.commit(repo.generate_commit_message(message=message, cmd="mv",
                                                 destination=str(destination)))


def new(repo: OnyoRepo,
        path: Optional[list[Path]],
        template: Optional[str],
        tsv: Optional[Path],
        keys: Dict[str, str],
        edit: bool,
        yes: bool,
        message: Union[list[str], None]) -> None:

    from onyo.lib.assets import read_assets_from_tsv, create_assets_in_destination, read_assets_from_CLI
    # verify that arguments do not conflict, otherwise exit
    validate_args_for_new(tsv, path, template)

    # read and verify the information for new assets from TSV and CLI
    # Note: Dict; keys are paths, values content
    assets = {}
    if tsv:
        assets = read_assets_from_tsv(tsv, template, keys, repo)
    elif path:
        # Note, this is currently not an `else`, b/c static code analysis (i.e. pyre) can't figure out,
        # that we would have failed before if neither `tsv` nor `path` was given.
        assets = read_assets_from_CLI(path, template, keys, repo)
    if not assets:
        raise ValueError("No new assets given.")

    # create all assets (and non-existing folder), and set their contents
    create_assets_in_destination(assets, repo)

    if edit:
        editor = get_editor(repo)
        # Note: This is different from the `edit` command WRT validation. Prob. just call the edit command?
        for asset in assets:
            edit_asset(editor, asset)
            repo.git.add(asset)

    # TODO: validate assets before offering to commit. This has to be done after
    # they are build, their values are set, and they where opened to edit

    # print diff-like output and remember new directories and assets
    staged = sorted(repo.git.files_staged)
    changes = []
    if staged:
        print("The following will be created:")
        for path in staged:
            # display new folders, not anchors.
            if ".anchor" in str(path):
                print(path.parent)
                changes.append(path.parent)
            else:
                print(path)
                changes.append(path)

    # commit or discard changes
    if yes or request_user_response("Create assets? (y/n) "):
        repo.git.commit(repo.generate_commit_message(message=message,
                                                     cmd="new"))
    else:
        repo.git._git(["rm", "-rf"] + [str(path) for path in changes])
        print('No new assets created.')


def rm(repo: OnyoRepo,
       path: list[Path],
       quiet: bool,
       yes: bool,
       message: Union[list[str], None]) -> None:
    from onyo.lib.command_utils import rm as onyo_rm
    # check flags
    if quiet and not yes:
        raise ValueError('The --quiet flag requires --yes.')

    if not quiet:
        dryrun_list = onyo_rm(repo, path, dryrun=True)
        print('The following will be deleted:\n' +
              '\n'.join(dryrun_list))

        if not yes and not request_user_response("Save changes? No discards all changes. (y/n) "):
            print('Nothing was deleted.')
            return

    onyo_rm(repo, path)
    repo.git.commit(repo.generate_commit_message(message=message,
                                                 cmd="rm"))


def set_(repo: OnyoRepo,
         paths: Iterable[Path],
         keys: Dict[str, Union[str, int, float]],
         dryrun: bool,
         rename: bool,
         depth: Union[int],
         quiet: bool,
         yes: bool,
         message: Union[list[str], None]) -> Union[str, None]:
    from onyo.lib.command_utils import set_assets

    # check flags for conflicts
    if quiet and not yes:
        raise ValueError('The --quiet flag requires --yes.')

    non_inventory_paths = [str(p) for p in paths if not repo.is_asset_path(p) and not repo.is_inventory_dir(p)]
    if non_inventory_paths:
        raise ValueError("The following paths are neither an inventory directory nor an asset:\n%s",
                         "\n".join(non_inventory_paths))

    diff = set_assets(repo, paths, keys, dryrun, rename, depth)

    # display changes
    if not quiet and diff:
        print("The following assets will be changed:")
        print(diff)
    elif quiet:
        pass
    else:
        print("The values are already set. No assets updated.")
        return

    # commit or discard changes
    staged = sorted(repo.git.files_staged)
    if staged:
        if yes or request_user_response("Update assets? (y/n) "):
            repo.git.commit(repo.generate_commit_message(message=message,
                                                         cmd="set",
                                                         keys=[f"{k}={v}" for k, v in keys.items()]))
        else:
            repo.git.restore()
            # when names were changed, the first restoring just brings
            # back the name, but leaves working-tree unclean
            if repo.git.files_staged:
                repo.git.restore()
            if not quiet:
                print("No assets updated.")


def tree(repo: OnyoRepo, paths: list[Path]) -> None:
    # sanitize the paths
    non_inventory_dirs = [str(p) for p in paths if not repo.is_inventory_dir(p)]
    if non_inventory_dirs:
        raise ValueError("The following paths are not inventory directories: %s" %
                         '\n'.join(non_inventory_dirs))

    # run it
    ret = subprocess.run(
        ['tree', *map(str, paths)], capture_output=True, text=True)
    # check for errors
    if ret.stderr:
        raise RuntimeError(ret.stderr)
    # print tree output
    print(ret.stdout)


def unset(repo: OnyoRepo,
          paths: Iterable[Path],
          keys: list[str],
          dryrun: bool,
          quiet: bool,
          yes: bool,
          depth: Union[int, None],
          message: Union[list[str], None]) -> None:
    from onyo.lib.command_utils import unset as ut_unset
    # check flags for conflicts
    if quiet and not yes:
        raise ValueError("The --quiet flag requires --yes.")

    non_inventory_paths = [str(p) for p in paths if not repo.is_asset_path(p) and not repo.is_inventory_dir(p)]
    if non_inventory_paths:
        raise ValueError("The following paths are neither an inventory directory nor an asset:\n%s",
                         "\n".join(non_inventory_paths))

    diff = ut_unset(repo, paths, keys, dryrun, quiet, depth)

    # display changes
    if not quiet and diff:
        print("The following assets will be changed:")
        print(diff)
    elif quiet:
        pass
    else:
        print("No assets containing the specified key(s) could be found. No assets updated.")
        return

    # commit or discard changes
    staged = sorted(repo.git.files_staged)
    if staged:
        if yes or request_user_response("Update assets? (y/n) "):
            repo.git.commit(repo.generate_commit_message(message=message,
                                                         cmd="unset",
                                                         keys=keys))
        else:
            repo.git.restore()
            # when names were changed, the first restoring just brings
            # back the name, but leaves working-tree unclean
            if repo.git.files_staged:
                repo.git.restore()
            if not quiet:
                print("No assets updated.")