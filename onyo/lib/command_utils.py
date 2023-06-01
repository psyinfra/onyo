from __future__ import annotations

import csv
import logging
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from shlex import quote
from typing import Dict, Union, Generator, Iterable, Optional

from rich.console import Console
from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from .onyo import OnyoRepo
from .exceptions import OnyoProtectedPathError, OnyoInvalidFilterError
from .filters import Filter, UNSET_VALUE


log: logging.Logger = logging.getLogger('onyo.command_utils')

# Note: Several functions only stage changes. Implies: This function somewhat
# assumes commit to be called later, which is out of its own control.
# May be better to only do the modification and have the caller take care of
# what to do with those modifications.
# Related: Staging probably not necessary. We can commit directly. Saves
# overhead for git-calls and would only have a different effect if changes were
# already staged before an onyo operation and are to be included in the commit.
# Which sounds like a bad idea, b/c of obfuscating history. So, probably:
# have functions to assemble paths/modifications and commit at once w/o staging
# anything in-between.


# Note: logging for user messaging rather than logging progress along internal
# call paths. DataLad does, too, and it's bad. Conflates debugging with "real"
# output.


def is_move_mode(sources: list[Union[Path]],
                 destination: Path) -> bool:
    """
    `mv()` can be used to either move or rename a file/directory. The mode
    is not explicitly declared by the user, and must be inferred from the
    arguments.

    Returns True if "move" mode and False if not.
    """
    # Note: This is internal `onyo mv` logic. Determine whether it's a move or a
    #       renaming based on argument properties. Called in "sanitize", though.

    # can only rename one item
    if len(sources) > 1:
        return True

    if destination.is_dir():
        return True

    # explicitly restating the source name at the destination is a move
    if sources[0].name == destination.name and not destination.exists():
        return True

    return False


def update_names(repo: OnyoRepo,
                 assets: list[Path],
                 name_values: Dict[str, Union[float, int, str]]) -> None:
    """
    Set the pseudo key fields of an assets name (rename an asset file) from
    values of a dictionary and test that the new name is valid and
    available.
    """
    from .assets import generate_new_asset_names
    for old, new in generate_new_asset_names(repo, repo.asset_paths, assets, name_values):
        repo.git._git(["mv", str(old), str(new)])


def sanitize_args_config(git_config_args: list[str]) -> list[str]:
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
            log.error("The following options cannot be used with onyo config:")
            log.error('\n'.join(forbidden_flags))
            log.error("\nExiting. Nothing was set.")
            sys.exit(1)
    return git_config_args


def get_editor(repo: OnyoRepo) -> str:
    """
    Returns the editor, progressing through git, onyo, $EDITOR, and finally
    fallback to "nano".
    """
    # onyo config and git config
    editor = repo.git.get_config('onyo.core.editor')

    # $EDITOR environment variable
    if not editor:
        log.debug("onyo.core.editor is not set.")
        editor = os.environ.get('EDITOR')

    # fallback to nano
    if not editor:
        log.debug("$EDITOR is also not set.")
        editor = 'nano'

    return editor


def request_user_response(question: str) -> bool:
    """
    Opens a dialog for the user and reads an answer from the keyboard.
    Returns True when user answers yes, False when no, and asks again if the
    input is neither.
    """
    while True:
        answer = input(question)
        if answer in ['y', 'Y', 'yes']:
            return True
        elif answer in ['n', 'N', 'no']:
            return False
    return False


def edit_asset(editor: str, asset: Path) -> bool:
    """
    Open an existing asset with `editor`. After changes are made, check the
    asset for validity and check its YAML syntax. If valid, write the changes,
    otherwise open a dialog and ask the user if the asset should be corrected
    or the changes discarded.

    Returns True when the asset was changed and saved without errors, and False
    if the user wants to discard the changes.
    """
    while True:
        os.system(f'{editor} {quote(str(asset))}')
        try:
            YAML(typ='rt').load(asset)
            # TODO: add asset validity here
            return True
        except scanner.ScannerError:
            print(f"{asset} has invalid YAML syntax.", file=sys.stderr)

        if not request_user_response("Continue editing? No discards changes. (y/n) "):
            break
    return False


def sanitize_keys(k: list[str], defaults: list) -> list[str]:
    """
    Remove duplicates from k while preserving key order and return default
    (pseudo) keys if k is empty
    """
    seen = set()
    k = [x for x in k if not (x in seen or seen.add(x))]
    return k if k else defaults


def set_filters(
        filters: list[str], repo: OnyoRepo, rich: bool = False) -> list[Filter]:
    """Create filters and check if there are no duplicate filter keys"""
    # Note: This is part of the get command

    init_filters = []
    try:
        init_filters = [Filter(f) for f in filters]
    except OnyoInvalidFilterError as exc:
        if rich:
            console = Console(stderr=True)
            console.print(f'[red]FAILED[/red] {exc}')
        else:
            print(exc, file=sys.stderr)
        # TODO: This raise replaces a sys.exit; Ultimately error messages above should be integrated in exception and
        #       rendering/printing handled upstairs.
        raise

    # ensure there are no duplicate filter keys
    duplicates = [
        x for x, i in Counter([f.key for f in init_filters]).items() if i > 1]
    if duplicates:
        if rich:
            console = Console(stderr=True)
            console.print(
                f'[red]FAILED[/red] Duplicate filter keys: {duplicates}')
        else:
            print(f'Duplicate filter keys: {duplicates}', file=sys.stderr)
        # TODO: This raise replaces a sys.exit; Ultimately error messages above should be integrated in exception and
        #       rendering/printing handled upstairs.
        raise ValueError
    return init_filters


def fill_unset(
        assets: Generator[tuple[Path, dict[str, str]], None, None],
        keys: list, unset: str = UNSET_VALUE) -> Generator:
    """
    If a key is not present for an asset, define it as `unset`.
    """
    unset_keys = {key: unset for key in keys}
    for asset, data in assets:
        yield asset, unset_keys | data


def natural_sort(
        assets: list[tuple[Path, dict[str, str]]],
        keys: Union[list, None] = None, reverse: bool = False) -> list:
    """
    Sort the output of `Repo.get()` by a given list of `keys` or by the path
    of the `assets` if no `keys` are provided.
    """
    if keys:
        for key in reversed(keys):
            assets = sorted(
                assets,
                key=lambda x: [
                    int(s) if s.isdigit() else s.lower() for s in
                    re.split('([0-9]+)', str(x[1][key]))],
                reverse=reverse)
    else:
        assets = sorted(
            assets,
            key=lambda x: [
                int(s) if s.isdigit() else s.lower()
                for s in re.split('([0-9]+)', str(x[0]))],
            reverse=reverse)

    return assets


def get_history_cmd(interactive: bool, repo: OnyoRepo) -> str:
    """
    Get the command used to display history. The appropriate one is selected
    according to the interactive mode, and basic checks are performed for
    validity.

    Returns the command on success.
    """
    history_cmd = None
    config_name = 'onyo.history.interactive'

    if not interactive or not sys.stdout.isatty():
        config_name = 'onyo.history.non-interactive'

    history_cmd = repo.git.get_config(config_name)
    if not history_cmd:
        raise ValueError(f"'{config_name}' is unset and is required to display history.\n"
                         f"Please see 'onyo config --help' for information about how to set it.")

    history_program = history_cmd.split()[0]
    if not shutil.which(history_program):
        raise ValueError(f"'{history_cmd}' acquired from '{config_name}'. "
                         f"The program '{history_program}' was not found. Exiting.")

    return history_cmd


def validate_args_for_new(tsv: Optional[Path],
                          path: Optional[list[Path]],
                          template: Optional[str]) -> None:
    """
    Some arguments conflict with each other, e.g. it has to be checked that the
    information from a tsv table does not conflict with the information from
    the command line.
    """
    # have either tsv table describing paths and asset names, or have it as
    # input argument, but not both.
    if tsv and path:
        raise ValueError("Can't have asset(s) and tsv file given.")
    if not tsv and not path:
        raise ValueError("Either asset(s) or a tsv file must be given.")

    if tsv:
        if not tsv.is_file():
            raise ValueError(f"{str(tsv)} does not exist.")
        with tsv.open('r') as tsv_file:
            table = csv.reader(tsv_file, delimiter='\t')
            # Note: Next lines can prob. be reduced to `header = table.next()`
            header = []
            # check that the first row (header) is complete
            for row in table:
                header = row
                break
            if not all(field in header for field in ['type', 'make', 'model', 'serial', 'directory']):
                raise ValueError("onyo new --tsv needs columns 'type', 'make', 'model', 'serial' and 'directory'.")
            if template and 'template' in header:
                raise ValueError("Can't use --template and template column in tsv.")


def rm(repo: OnyoRepo,
       paths: Union[Iterable[Path], Path],
       dryrun: bool = False) -> list[str]:
    """
    Delete ``asset``\\(s) and ``directory``\\(s).
    """
    # Note: This doesn't commit. For some reason this is done at the CLI layer
    # in case of this command.

    if not isinstance(paths, (list, set)):
        paths = [paths]

    paths_to_rm = []
    invalid_paths = []
    for p in paths:
        if repo.is_asset_path(p) or repo.is_inventory_dir(p):
            paths_to_rm.append(p)
        else:
            invalid_paths.append(p)
    if invalid_paths:
        raise ValueError("The following paths are neither inventory directories nor assets:\n%s"
                         "\nNothing was deleted." % '\n'.join(map(str, invalid_paths)))

    git_rm_cmd = ['rm', '-r']
    if dryrun:
        git_rm_cmd.append('--dry-run')
    git_rm_cmd.extend([str(x) for x in paths_to_rm])
    # Note: This comment is a lie - nothing's committed
    # rm and commit
    ret = repo.git._git(git_rm_cmd)

    # TODO: change this to info
    log.debug('The following will be deleted:\n' +
              '\n'.join([str(x.relative_to(repo.git.root)) for x in paths_to_rm]))

    # Note: The usual "invalidate everything because we don't know what we did".
    repo.clear_caches()
    # return a list of rm-ed assets
    # TODO: should this also list the dirs?
    # TODO: is this relative to opdir or root? (should be opdir)
    # Note: NO. It's root!
    # ben@tree in /tmp/some/some on git:master
    # ❱ tree
    # .
    # └── where
    #     └── file
    #
    # 2 directories, 1 file
    # ben@tree in /tmp/some/some on git:master
    # ❱ git rm where/file
    # rm 'some/where/file'

    # Note: Why is this parsing the output? The command didn't fail, we know
    # what we told it, and we don't double-check whether the output matches
    # expectation. Either don't bother at all, or simply let git-rm do the
    # output, instead of catching and parsing it only in order to spit out the
    # same thing again.
    # The only reason to do it is, so we can swallow it the second time (running
    # dry-run first and then for real)

    return [r for r in re.findall("rm '(.*)'", ret)]


def set_assets(repo: OnyoRepo,
               paths: Iterable[Path],
               values: Dict[str, Union[str, int, float]],
               dryrun: bool,
               rename: bool,
               depth: Union[int]) -> str:
    """
    Set values for a list of assets (or directories), or rename assets
    through updating their name fields.

    A flag enable to limit the depth of recursion for setting values in
    directories.
    """

    from .assets import get_asset_content, get_asset_files_by_path, write_asset_file, PSEUDO_KEYS, generate_new_asset_names
    assets_to_set = get_asset_files_by_path(repo.asset_paths, paths, depth)

    # Note: This separation may not be necessary. We can check whether any key is in fact a pseudo key
    # (in order to fail w/o rename)
    # But represent ALL key-value pairs in one dict. An Asset object (or alike) can then consider what to do with a key
    # based on whatever is configured to be a pseudo-key.
    content_values = dict((field, values[field]) for field in values.keys() if field not in PSEUDO_KEYS)
    name_values = dict((field, values[field]) for field in values.keys() if field in PSEUDO_KEYS)

    if name_values and not rename:
        raise ValueError("Can't change pseudo keys without --rename.")

    if content_values:
        for asset_path in assets_to_set:
            contents = get_asset_content(asset_path)
            contents.update(content_values)
            write_asset_file(asset_path, contents)
            repo.git.add(asset_path)

    if name_values:
        try:
            for old, new in generate_new_asset_names(repo, repo.asset_paths, assets_to_set, name_values):
                repo.git._git(["mv", str(old), str(new)])

        except ValueError:
            # Note: repo.files_staged is cached. How do we know, it's accounting for what we just have done?
            #       This implies to assume this is the first time the property is accessed.
            if repo.git.files_staged:
                repo.git.restore()
            # reset renaming needs double-restoring
            if repo.git.files_staged:
                repo.git.restore()
            raise

    # generate diff, and restore changes for dry-runs
    diff = repo.git._diff_changes()
    if diff and dryrun:
        repo.git.restore()

    # Note: Here, too, everything is invalidated regardless of what was actually done.
    repo.clear_caches()
    return diff


def unset(repo: OnyoRepo,
          paths: Iterable[Path],
          keys: list[str],
          dryrun: bool,
          quiet: bool,
          depth: Union[int, None]) -> str:

    from .assets import get_asset_files_by_path, unset_asset_keys, PSEUDO_KEYS
    # set and unset should select assets exactly the same way
    assets_to_unset = get_asset_files_by_path(repo.asset_paths, paths, depth)

    if any([key in PSEUDO_KEYS for key in keys]):
        raise ValueError("Can't unset pseudo keys (name fields are required).")

    unset_assets = []
    for asset in assets_to_unset:
        unset_asset_keys(asset, keys, quiet)
        unset_assets.append(asset)
    repo.git.add(unset_assets)

    # generate diff, and restore changes for dry-runs
    diff = repo.git._diff_changes()
    if diff and dryrun:
        repo.git.restore()

    return diff


def sanitize_destination_for_mv(repo: OnyoRepo,
                                sources: list[Path],
                                destination: Path) -> Path:
    """
    Perform a sanity check on the destination. This includes protected
    paths, conflicts, and other pathological scenarios.

    Returns an absolute Path on success.
    """

    error_path_conflict = []

    # Common checks
    # protected paths

    if not repo.is_inventory_dir(destination) and not repo.is_inventory_path(destination):  # 2nd condition sufficient to be rename target?
        # Note: Questionable message. This piece of code has no clue whether
        #       something was moved. That is done by the caller.
        raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                     f'{destination}\nNothing was moved.')

    # destination cannot be a file
    if destination.is_file():
        # This intentionally raises FileExistsError rather than NotADirectoryError.
        # It reduces the number of different exceptions that can be raised
        # by `mv()`, and keeps the exception type unified with other similar
        # situations (such as implicit conflict with the destination).
        raise FileExistsError(f"The destination '{destination}' cannot be a file.\n" +
                              'Nothing was moved.')

    # check for conflicts and general insanity
    for src in sources:
        new_path = destination / src.name
        if not destination.exists():
            new_path = destination

        # cannot rename/move into self
        if src in new_path.parents:
            raise ValueError(f"Cannot move '{src}' into itself.\n" +
                             "Nothing was moved.")

        # target paths cannot already exist
        if new_path.exists():
            error_path_conflict.append(new_path)
            continue

    if error_path_conflict:
        # Note: See earlier; "Nothing was moved" has no business being here.
        raise FileExistsError(
            'The following destination paths exist and would conflict:\n{}'
            '\nNothing was moved.'.format(
                '\n'.join(map(str, error_path_conflict))))

    # parent must exist
    if not destination.parent.exists():
        raise FileNotFoundError(
            f"The destination '{destination.parent}' does not exist.\n"
            f"Nothing was moved.")

    if not is_move_mode(sources, destination):
        """
        Rename mode checks
        """
        log.debug("'mv' in rename mode")
        # renaming files is not allowed
        src = sources[0]
        if src.is_file() and src.name != destination.name:
            raise ValueError(
                f"Cannot rename asset '{src.name}' to "
                f"'{destination.name}'.\nUse 'set()' to rename assets.\n"
                f"Nothing was moved.")

        # target cannot already exist
        if destination.exists():
            raise FileExistsError(
                f"The destination '{destination}' exists and would "
                f"conflict.\nNothing was moved.")
    else:
        """
        Move mode checks
        """
        log.debug("'mv' in move mode")

        # check if same name is specified as the destination
        # (e.g. rename to same name is a move)
        if src.name != destination.name:
            # dest must exist
            if not destination.exists():
                raise FileNotFoundError(
                    f"The destination '{destination}' does not exist.\n"
                    f"Nothing was moved.")

        # cannot move onto self
        if src.is_file() and destination.is_file() and src.samefile(destination):
            raise FileExistsError(f"Cannot move '{src}' onto itself.\n" +
                                  "Nothing was moved.")

    return destination


def onyo_mv(repo: OnyoRepo,
            sources: Union[Iterable[Path], Path],
            destination: Path,
            dryrun: bool = False) -> list[tuple[str, str]]:
    # Note: For clarity in history, I think renaming (locations) and moving (assets) should be separated operations.

    if not isinstance(sources, (list, set)):
        sources = [sources]
    elif not isinstance(sources, list):
        sources = list(sources)

    # sanitize and validate arguments
    invalid_sources = [p
                       for p in sources
                       if not repo.is_asset_path(p) and
                       not repo.is_inventory_dir(p)]
    if invalid_sources:
        raise ValueError("The following paths are neither inventory directories nor assets:\n%s"
                         "\nNothing was moved.",
                         '\n'.join(map(str, invalid_sources)))

    dest_path = sanitize_destination_for_mv(repo, sources, destination)

    # Move block into method; However, depends on logic above: Can we turn that into inventory/onyorepo method
    # (moving assets, renaming locations) or plain gitrepo?
    git_mv_cmd = ['mv']
    if dryrun:
        git_mv_cmd.append('--dry-run')
    git_mv_cmd.extend([*map(str, sources), str(dest_path)])
    ret = repo.git._git(git_mv_cmd)

    # TODO: change this to info
    log.debug('The following will be moved:\n{}'.format('\n'.join(
        map(lambda x: str(x.relative_to(repo.git.root)), sources))))

    # Note: This is invalidating everything, because it pretends to not know what was actually done.
    #       That information lives in the sanitize functions for some reason.
    repo.clear_caches()  # might move or rename templates

    # return a list of mv-ed assets
    return [r for r in re.findall('Renaming (.*) to (.*)', ret)]
