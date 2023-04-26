import random
import re
import shutil
import string
from pathlib import Path
from typing import Dict, Iterable, Optional, Union, Generator, Set

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo import OnyoInvalidRepoError, OnyoProtectedPathError
from .onyo import Repo, log
from .filters import Filter


def fsck(repo: Repo, tests: Optional[list[str]] = None) -> None:
    all_tests = {
        "clean-tree": repo._fsck_clean_tree,
        "anchors": repo._fsck_anchors,
        "asset-unique": repo._fsck_unique_assets,
        "asset-yaml": repo._fsck_yaml,
        "asset-validity": repo._fsck_validation,
        "pseudo-keys": repo._fsck_pseudo_keys,
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
            log.debug(f"'{key}' failed")
            raise OnyoInvalidRepoError(f"'{repo._opdir}' failed fsck test '{key}'")

        log.debug(f"'{key}' succeeded")


def fsck_anchors(repo: Repo) -> bool:
    anchors_exist = {x for x in repo.files if x.name == '.anchor' and '.onyo' not in x.parts}
    anchors_expected = {x.joinpath('.anchor') for x in repo.dirs
                        if not repo._is_protected_path(x)}
    difference = anchors_expected.difference(anchors_exist)

    if difference:
        log.warning(
            'The following .anchor files are missing:\n'
            '{0}'.format('\n'.join(map(str, difference))))
        log.warning(
            "Likely 'mkdir' was used to create the directory. Use "
            "'onyo mkdir' instead.")
        # TODO: Prompt the user if they want Onyo to fix it.

        return False

    return True


def fsck_clean_tree(repo: Repo) -> bool:
    changed = {str(x) for x in repo.files_changed}
    staged = {str(x) for x in repo.files_staged}
    untracked = {str(x) for x in repo.files_untracked}

    if changed or staged or untracked:
        log.error('The working tree is not clean.')

        if changed:
            log.error('Changes not staged for commit:\n{}'.format(
                '\n'.join(map(str, changed))))

        if staged:
            log.error('Changes to be committed:\n{}'.format(
                '\n'.join(map(str, staged))))

        if untracked:
            log.error('Untracked files:\n{}'.format(
                '\n'.join(map(str, untracked))))

        log.error(
            'Please commit all changes or add untracked files to '
            '.gitignore')

        return False

    return True


def fsck_pseudo_keys(repo: Repo) -> bool:
    assets_failed = {}
    pseudo_keys = ["type", "make", "model", "serial"]

    for asset in repo.assets:
        violation_list = [
            x for x in pseudo_keys if x in repo._read_asset(asset)]
        if violation_list:
            assets_failed[asset] = violation_list

    if assets_failed:
        log.error(
            "Pseudo keys {0} are reserved for asset file names, and are "
            "not allowed in the asset's contents. The following assets "
            "contain pseudo keys:\n{1}".format(
                tuple(pseudo_keys),
                '\n'.join(
                    f'{k}: {", ".join(v)}'
                    for k, v in assets_failed.items())))

        return False

    return True


def fsck_unique_assets(repo: Repo) -> bool:
    asset_names = [a.name for a in repo.assets]
    duplicates = [a for a in repo.assets if asset_names.count(a.name) > 1]
    duplicates.sort(key=lambda x: x.name)

    if duplicates:
        log.error('The following file names are not unique:\n{}'.format(
            '\n'.join(map(str, duplicates))))
        return False

    return True


def fsck_validation(repo: Repo) -> bool:
    invalid = {}
    for asset in repo.assets:
        # TODO: validate assets
        pass

    if invalid:
        log.error(
            'The contents of the following files fail validation:\n'
            '{}'.format(
                '\n'.join([f'{k}\n{v}' for k, v in invalid.items()])))

        return False

    return True


def fsck_yaml(repo: Repo) -> bool:
    invalid_yaml = []

    for asset in repo.assets:
        # TODO: use valid_yaml()
        try:
            YAML(typ='rt').load(Path(repo.root, asset))
        except scanner.ScannerError:
            invalid_yaml.append(str(asset))

    if invalid_yaml:
        log.error('The following files fail YAML validation:\n{}'.format(
            '\n'.join(invalid_yaml)))

        return False

    return True


def init_onyo(repo: Repo, directory: Union[Path, str]) -> None:
    target_dir = repo._init_sanitize(directory)
    skel_dir = Path(Path(__file__).resolve().parent.parent, 'skel')
    dot_onyo = Path(target_dir, '.onyo')

    # create target if it doesn't already exist
    target_dir.mkdir(exist_ok=True)

    # git init (if needed)
    if Path(target_dir, '.git').exists():
        log.info(f"'{target_dir}' is already a git repository.")
    else:
        ret = repo._git(['init'], cwd=target_dir)
        log.info(ret.strip())

    # populate .onyo dir
    shutil.copytree(skel_dir, dot_onyo)

    # add and commit
    repo._git(['add', '.onyo/'], cwd=target_dir)
    repo._git(['commit', '-m', 'Initialize as an Onyo repository'], cwd=target_dir)

    log.info(f'Initialized Onyo repository in {dot_onyo}/')


def init_sanitize(directory: Union[Path, str]) -> Path:
    full_path = Path(directory).resolve()

    # target must be a directory
    if full_path.exists() and not full_path.is_dir():
        log.error(f"'{full_path}' exists but is not a directory.")
        raise FileExistsError(f"'{full_path}' exists but is not a directory.")

    # parent must exist
    if not full_path.parent.exists():
        log.error(f"'{full_path.parent}' does not exist.")
        raise FileNotFoundError(f"'{full_path.parent}' does not exist.")

    # cannot already be an .onyo repo
    dot_onyo = Path(full_path, '.onyo')
    if dot_onyo.exists():
        log.error(f"'{dot_onyo}' already exists.")
        raise FileExistsError(f"'{dot_onyo}' already exists.")

    return full_path


def mk_onyo_dir(repo: Repo, directories: Union[Iterable[Union[Path, str]], Path, str]) -> None:
    if not isinstance(directories, (list, set)):
        directories = [directories]

    dirs = repo._mkdir_sanitize(directories)
    # make dirs
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # anchors
    anchors = {Path(i, '.anchor') for d in dirs
               for i in [d] + list(d.parents)
               if i.is_relative_to(repo.root) and
               not i.samefile(repo.root)}
    for a in anchors:
        a.touch(exist_ok=True)

    repo.add(anchors)


def mkdir_sanitize(repo: Repo, dirs: Iterable[Union[Path, str]]) -> set[Path]:
    error_exist = []
    error_path_protected = []
    dirs_to_create = set()
    # TODO: the set() neatly avoids creating the same dir twice. Intentional?

    for d in dirs:
        full_dir = Path(repo.opdir, d).resolve()

        # check if it exists
        if full_dir.exists():
            error_exist.append(d)
            continue

        # protected paths
        if repo._is_protected_path(full_dir):
            error_path_protected.append(d)
            continue

        dirs_to_create.add(full_dir)

    # errors
    if error_exist:
        log.error(
            'The following paths already exist:\n{}\nNo directories were '
            'created.'.format('\n'.join(map(str, error_exist))))
        raise FileExistsError(
            'The following paths already exist:\n{}'.format(
                '\n'.join(map(str, error_exist))))

    if error_path_protected:
        log.error(
            'The following paths are protected by onyo:\n{}\nNo '
            'directories were created.'.format(
                '\n'.join(map(str, error_path_protected))))
        raise OnyoProtectedPathError(
            'The following paths are protected by onyo:\n{}'.format(
                '\n'.join(map(str, error_path_protected))))

    return dirs_to_create


def mv(repo: Repo,
       sources: Union[Iterable[Union[Path, str]], Path, str],
       destination: Union[Path, str],
       dryrun: bool = False) -> list[tuple[str, str]]:

    if not isinstance(sources, (list, set)):
        sources = [sources]
    elif not isinstance(sources, list):
        sources = list(sources)

    # sanitize and validate arguments
    src_paths = repo._mv_sanitize_sources(sources)
    dest_path = repo._mv_sanitize_destination(sources, destination)

    if dryrun:
        ret = repo._git(
            ['mv', '--dry-run', *map(str, src_paths), str(dest_path)])
    else:
        ret = repo._git(['mv', *map(str, src_paths), str(dest_path)])

    # TODO: change this to info
    log.debug('The following will be moved:\n{}'.format('\n'.join(
        map(lambda x: str(x.relative_to(repo.opdir)), src_paths))))

    repo.clear_caches(
        assets=True,  # `onyo mv` can change the dir of assets
        dirs=True,  # might move directories
        files=True,  # might move anchors
        templates=True)  # might move or rename templates

    # return a list of mv-ed assets
    # TODO: is this relative to opdir or root? (should be opdir)
    return [r for r in re.findall('Renaming (.*) to (.*)', ret)]


def mv_move_mode(repo: Repo,
                 sources: list[Union[Path, str]],
                 destination: Union[Path, str]) -> bool:
    # can only rename one item
    if len(sources) > 1:
        return True

    if Path(repo.opdir, destination).resolve().is_dir():
        return True

    # explicitly restating the source name at the destination is a move
    if Path(sources[0]).name == Path(destination).name and not Path(repo.opdir, destination).resolve().exists():
        return True

    return False


def mv_sanitize_destination(repo: Repo,
                            sources: list[Union[Path, str]],
                            destination: Union[Path, str]) -> Path:
    error_path_conflict = []
    dest_path = Path(repo.opdir, destination).resolve()

    """
    Common checks
    """
    # protected paths
    if repo._is_protected_path(dest_path):
        log.error('The following paths are protected by onyo:\n' +
                  f'{dest_path}\n' +
                  'Nothing was moved.')
        raise OnyoProtectedPathError('The following paths are protected by onyo:\n' +
                                     f'{dest_path}')

    # destination cannot be a file
    if dest_path.is_file():
        # This intentionally raises FileExistsError rather than NotADirectoryError.
        # It reduces the number of different exceptions that can be raised
        # by `mv()`, and keeps the exception type unified with other similar
        # situations (such as implicit conflict with the destination).
        log.error(f"The destination '{dest_path}' cannot be a file.\n" +
                  'Nothing was moved.')
        raise FileExistsError(f"The destination '{dest_path}' cannot be a file.\n" +
                              'Nothing was moved.')

    # check for conflicts and general insanity
    for src in sources:
        src_path = Path(repo.opdir, src).resolve()
        new_path = Path(dest_path, src_path.name).resolve()
        if not dest_path.exists:
            new_path = Path(dest_path).resolve()

        # cannot rename/move into self
        if src_path in new_path.parents:
            log.error(f"Cannot move '{src}' into itself.\n" +
                      "Nothing was moved.")
            raise ValueError(f"Cannot move '{src}' into itself.\n" +
                             "Nothing was moved.")

        # target paths cannot already exist
        if new_path.exists():
            error_path_conflict.append(new_path)
            continue

    if error_path_conflict:
        log.error(
            'The following destinations exist and would conflict:\n{}\n'
            'Nothing was moved.'.format(
                '\n'.join(map(str, error_path_conflict))))
        raise FileExistsError(
            'The following destination paths exist and would conflict:\n{}'
            '\nNothing was moved.'.format(
                '\n'.join(map(str, error_path_conflict))))

    # parent must exist
    if not dest_path.parent.exists():
        log.error(
            f"The destination '{dest_path.parent}' does not exist.\n"
            f"Nothing was moved.")
        raise FileNotFoundError(
            f"The destination '{dest_path.parent}' does not exist.\n"
            f"Nothing was moved.")

    if repo._mv_rename_mode(sources, destination):
        """
        Rename mode checks
        """
        log.debug("'mv' in rename mode")
        # renaming files is not allowed
        src_path = Path(repo.opdir, sources[0]).resolve()
        if src_path.is_file() and src_path.name != dest_path.name:
            log.error(
                f"Cannot rename asset '{src_path.name}' to "
                f"'{dest_path.name}'.\nUse 'set()' to rename assets.\n"
                f"Nothing was moved.")
            raise ValueError(
                f"Cannot rename asset '{src_path.name}' to "
                f"'{dest_path.name}'.\nUse 'set()' to rename assets.\n"
                f"Nothing was moved.")

        # target cannot already exist
        if dest_path.exists():
            log.error(
                f"The destination '{dest_path}' exists and would "
                f"conflict.\nNothing was moved.")
            raise FileExistsError(
                f"The destination '{dest_path}' exists and would "
                f"conflict.\nNothing was moved.")
    else:
        """
        Move mode checks
        """
        log.debug("'mv' in move mode")

        # check if same name is specified as the destination
        # (e.g. rename to same name is a move)
        if src_path.name != dest_path.name:
            # dest must exist
            if not dest_path.exists():
                log.error(
                    f"The destination '{destination}' does not exist.\n"
                    f"Nothing was moved.")
                raise FileNotFoundError(
                    f"The destination '{destination}' does not exist.\n"
                    f"Nothing was moved.")

        # cannot move onto self
        if src_path.is_file() and dest_path.is_file() and src_path.samefile(dest_path):
            log.error(f"Cannot move '{src}' onto itself.\n" +
                      "Nothing was moved.")
            raise FileExistsError(f"Cannot move '{src}' onto itself.\n" +
                                  "Nothing was moved.")

    return dest_path


def mv_rename_mode(repo: Repo,
                   sources: list[Union[Path, str]],
                   destination: Union[Path, str]) -> bool:
    return not repo._mv_move_mode(sources, destination)


def mv_sanitize_sources(repo: Repo, sources: list[Union[Path, str]]) -> list[Path]:
    paths_to_mv = []
    error_path_absent = []
    error_path_protected = []

    # validate sources
    for src in sources:
        full_path = Path(repo.opdir, src).resolve()

        # paths must exist
        if not full_path.exists():
            error_path_absent.append(src)
            continue

        # protected paths
        if repo._is_protected_path(full_path):
            error_path_protected.append(src)
            continue

        paths_to_mv.append(full_path)

    if error_path_absent:
        log.error(
            'The following source paths do not exist:\n{}\nNothing was '
            'moved.'.format('\n'.join(map(str, error_path_absent))))
        raise FileNotFoundError(
            'The following source paths do not exist:\n{}'.format(
                '\n'.join(map(str, error_path_absent))))

    if error_path_protected:
        log.error(
            'The following paths are protected by onyo:\n{}\nNothing was '
            'moved.'.format('\n'.join(map(str, error_path_protected))))
        raise OnyoProtectedPathError(
            'The following paths are protected by onyo:\n{}'.format(
                '\n'.join(map(str, error_path_protected))))

    return paths_to_mv


def generate_faux_serials(repo: Repo,
                          length: int = 6,
                          num: int = 1) -> set[str]:
    if length < 4:
        # 62^4 is ~14.7 million combinations. Which is the lowest acceptable
        # risk of collisions between independent checkouts of a repo.
        raise ValueError('The length of faux serial numbers must be >= 4.')

    if num < 1:
        raise ValueError('The length of faux serial numbers must be >= 1.')

    alphanum = string.ascii_letters + string.digits
    faux_serials = set()
    repo_faux_serials = {str(x.name).split('faux')[-1] for x in repo.assets}

    while len(faux_serials) < num:
        serial = ''.join(random.choices(alphanum, k=length))
        if serial not in repo_faux_serials:
            faux_serials.add(f'faux{serial}')

    return faux_serials


def get_template(repo: Repo,
                 template_name: Union[Path, str, None] = None) -> Path:
    if not template_name:
        template_name = repo.get_config('onyo.new.template')
        if template_name is None:
            log.error("Either --template must be given or 'onyo.new.template' must be set.")
            raise ValueError("Either --template must be given or 'onyo.new.template' must be set.")

    template_name = Path(template_name)
    for template in repo.templates:
        if template.name == template_name.name:
            return template
        elif template_name.is_file() and template.samefile(template_name):
            return template

    log.error(f"Template {template_name} does not exist.")
    raise ValueError(f"Template {template_name} does not exist.")


def valid_asset_path_and_name_available(repo: Repo,
                                        asset: Path,
                                        new_assets: list[Path]) -> None:
    if not repo.valid_name(asset):
        log.error(f"'{asset}' is not a valid asset name.")
        raise ValueError(f"'{asset}' is not a valid asset name.")
    if file := [file for file in repo.assets if asset.name == file.name]:
        log.error(f"Filename '{asset.name}' already exists as '{file[0]}'.")
        raise ValueError(f"Filename '{asset.name}' already exists as '{file[0]}'.")
    elif file := [file for file in new_assets if asset.name == file.name]:
        log.error(f"Input contains multiple '{file[0].name}'")
        raise ValueError(f"Input contains multiple '{file[0].name}'")
    if repo._is_protected_path(asset):
        log.error(f"The path is protected by onyo: '{asset}'")
        raise ValueError(f"Input contains multiple '{file[0].name}'")


def valid_name(asset: Union[Path, str]) -> bool:
    asset = Path(asset)

    try:
        re.findall(r'(^[^._]+?)_([^._]+?)_([^._]+?)\.(.+)', asset.name)[0]
    except (ValueError, IndexError):
        log.info(f"'{asset.name}' must be in the format '<type>_<make>_<model>.<serial>'")
        return False

    return True


def set_assets(repo: Repo,
               paths: Iterable[Union[Path, str]],
               values: Dict[str, Union[str, int, float]],
               dryrun: bool,
               rename: bool,
               depth: Union[int]) -> str:
    assets_to_set = repo._get_assets_by_path(paths, depth)

    content_values = dict((field, values[field]) for field in values.keys() if field not in ["type", "make", "model", "serial"])
    name_values = dict((field, values[field]) for field in values.keys() if field in ["type", "make", "model", "serial"])

    if name_values and not rename:
        log.error("Can't change pseudo keys without --rename.")
        raise ValueError("Can't change pseudo keys without --rename.")

    if content_values:
        for asset in assets_to_set:
            contents = repo._read_asset(asset)
            contents.update(content_values)
            repo._write_asset(asset, contents)
            repo.add(asset)

    if name_values:
        try:
            repo._update_names(assets_to_set, name_values)
        except ValueError as e:
            if repo.files_staged:
                repo.restore()
            # reset renaming needs double-restoring
            if repo.files_staged:
                repo.restore()
            raise ValueError(e)

    # generate diff, and restore changes for dry-runs
    diff = repo._diff_changes()
    if diff and dryrun:
        repo.restore()

    repo.clear_caches(assets=True,  # `onyo set` can rename assets
                      dirs=False,  # `set` cannot create, move, or remove directories
                      files=True,  # might rename asset files
                      templates=True  # might modify templates
                      )
    return diff


def update_names(repo: Repo,
                 assets: list[Path],
                 name_values: Dict[str, Union[float, int, str]]) -> None:
    new_assets = []

    # count and request the needed faux serial numbers
    faux_serial_list = []
    if 'serial' in name_values.keys() and name_values['serial'] == 'faux':
        faux_number = len(assets)
        if faux_number > 0:
            faux_serial_list = repo.generate_faux_serials(num=faux_number)

    for asset in assets:
        # split old name into parts
        [serial, model, make, type] = [field[::-1] for field in re.findall(r'(.*)\.(.*)_(.*)_(.*)', asset.name[::-1])[0]]
        fields = name_values.keys()

        # update name fields and build new asset name
        if "serial" in fields:
            if name_values["serial"] == "faux":
                serial = faux_serial_list.pop()
            else:
                serial = name_values["serial"]
        if "model" in fields:
            model = name_values["model"]
        if "make" in fields:
            make = name_values["make"]
        if "type" in fields:
            type = name_values["type"]
        new_name = Path(asset.parent, f"{type}_{make}_{model}.{serial}")

        # Check validity of the new asset name
        if new_name == asset.name:
            log.error(f"New asset names must be different than old names: '{new_name}'")
            raise ValueError(f"New asset names must be different than old names: '{new_name}'")

        if not repo.valid_name(new_name):
            log.error(f"New asset name is not valid: '{new_name}'")
            raise ValueError(f"New asset name is not valid: '{new_name}'")

        repo.valid_asset_path_and_name_available(new_name, new_assets)
        new_assets.append(new_name)

        repo._git(["mv", str(asset), str(new_name)])


def rm(repo: Repo,
       paths: Union[Iterable[Union[Path, str]], Path, str],
       dryrun: bool = False) -> list[str]:

    if not isinstance(paths, (list, set)):
        paths = [paths]

    paths_to_rm = repo._rm_sanitize(paths)

    if dryrun:
        ret = repo._git(['rm', '-r', '--dry-run'] + [str(x) for x in paths_to_rm])
    else:
        # rm and commit
        ret = repo._git(['rm', '-r'] + [str(x) for x in paths_to_rm])

    # TODO: change this to info
    log.debug('The following will be deleted:\n' +
              '\n'.join([str(x.relative_to(repo.opdir)) for x in paths_to_rm]))

    repo.clear_caches(assets=True,  # `onyo rm` can delete assets
                      dirs=True,  # can delete directories
                      files=True,  # if used on dir, deletes also `.anchor`
                      templates=True  # can delete templates
                      )
    # return a list of rm-ed assets
    # TODO: should this also list the dirs?
    # TODO: is this relative to opdir or root? (should be opdir)
    return [r for r in re.findall("rm '(.*)'", ret)]


def rm_sanitize(repo: Repo, paths: Iterable[Union[Path, str]]) -> list[Path]:
    error_path_absent = []
    error_path_protected = []
    paths_to_rm = []

    for p in paths:
        full_path = Path(repo.opdir, p).resolve()

        # paths must exist
        if not full_path.exists():
            error_path_absent.append(p)
            continue

        # protected paths
        if repo._is_protected_path(full_path):
            error_path_protected.append(p)
            continue

        paths_to_rm.append(full_path)

    if error_path_absent:
        log.error(
            'The following paths do not exist:\n{}\nNothing was '
            'deleted.'.format('\n'.join(map(str, error_path_absent))))

        raise FileNotFoundError(
            'The following paths do not exist:\n{}'.format(
                '\n'.join(map(str, error_path_absent))))

    if error_path_protected:
        log.error(
            'The following paths are protected by onyo:\n{}\nNo '
            'directories were created.'.format(
                '\n'.join(map(str, error_path_protected))))
        raise OnyoProtectedPathError(
            'The following paths are protected by onyo:\n{}'.format(
                '\n'.join(map(str, error_path_protected))))

    return paths_to_rm


def unset(repo: Repo,
          paths: Iterable[Union[Path, str]],
          keys: list[str],
          dryrun: bool,
          quiet: bool,
          depth: Union[int]) -> str:
    # set and unset should select assets exactly the same way
    assets_to_unset = repo._get_assets_by_path(paths, depth)

    if any([key in ["type", "make", "model", "serial"] for key in keys]):
        log.error("Can't unset pseudo keys (name fields are required).")
        raise ValueError("Can't unset pseudo keys (name fields are required).")

    for asset in assets_to_unset:
        contents = repo._read_asset(asset)

        for field in keys:
            try:
                del contents[field]
            except KeyError:
                if not quiet:
                    log.info(f"Field {field} does not exist in {asset}")

        repo._write_asset(asset, contents)
        repo.add(asset)

    # generate diff, and restore changes for dry-runs
    diff = repo._diff_changes()
    if diff and dryrun:
        repo.restore()

    return diff


def get(repo: Repo,
        keys: Set[str],
        paths: Set[Path],
        depth: Union[int, None] = None,
        filters: Union[list[Filter], None] = None) -> Generator:
    # filter assets by path and depth relative to paths
    assets = repo._get_assets_by_path(paths, depth) or []

    if filters:
        # Filters that do not require loading an asset are applied first
        filters.sort(key=lambda x: x.is_pseudo, reverse=True)

        # Remove assets that do not match all filters
        for f in filters:
            assets[:] = filter(f.match, assets)

    # Obtain keys from remaining assets
    assets = ((a, {
        k: v
        for k, v in (repo._read_asset(a) | dict(zip(
            repo.pseudo_keys, re.findall(
                r'(^[^._]+?)_([^._]+?)_([^._]+?)\.(.+)',
                a.name)[0]))).items()
        if k in keys}) for a in assets)

    return assets
