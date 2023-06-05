from __future__ import annotations
import logging
import csv
import random
import re
import string
import sys
from pathlib import Path
from typing import Dict, Union, Iterable, Set, Generator, Optional

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo.lib.filters import Filter
from onyo.lib.onyo import OnyoRepo


log: logging.Logger = logging.getLogger('onyo.assets')

# Note: Order in this definition likely matters, since the filename is made of them:
PSEUDO_KEYS = ["type", "make", "model", "serial"]


def contains_no_pseudo_keys(asset_files: Set[Path]) -> bool:
    # Note: This actually operates on content, not on files/paths

    assets_failed = {}

    for asset in asset_files:
        violation_list = [
            x for x in PSEUDO_KEYS if x in get_asset_content(asset)]
        if violation_list:
            assets_failed[asset] = violation_list

    if assets_failed:
        log.error(
            "Pseudo keys {0} are reserved for asset file names, and are "
            "not allowed in the asset's contents. The following assets "
            "contain pseudo keys:\n{1}".format(
                tuple(PSEUDO_KEYS),
                '\n'.join(
                    f'{k}: {", ".join(v)}'
                    for k, v in assets_failed.items())))

        return False

    return True


def has_unique_names(asset_files: Set[Path]) -> bool:
    asset_names = [a.name for a in asset_files]
    duplicates = [a for a in asset_files if asset_names.count(a.name) > 1]
    duplicates.sort(key=lambda x: x.name)

    if duplicates:
        log.error('The following file names are not unique:\n{}'.format(
            '\n'.join(map(str, duplicates))))
        return False

    return True


def validate_assets(asset_files: Set[Path]) -> bool:
    invalid = {}
    for asset in asset_files:
        # TODO: validate assets
        pass

    if invalid:
        log.error(
            'The contents of the following files fail validation:\n'
            '{}'.format(
                '\n'.join([f'{k}\n{v}' for k, v in invalid.items()])))

        return False

    return True


def validate_yaml(asset_files: Set[Path]) -> bool:
    # Note: assumes absolute paths!
    invalid_yaml = []

    for asset in asset_files:
        # TODO: use valid_yaml()
        try:
            YAML(typ='rt').load(asset)
        except scanner.ScannerError:
            invalid_yaml.append(str(asset))

    if invalid_yaml:
        log.error('The following files fail YAML validation:\n{}'.format(
            '\n'.join(invalid_yaml)))

        return False

    return True


def get_faux_serials(asset_files: Set[Path],
                     length: int = 6,
                     num: int = 1) -> set[str]:
    """
    Generate a unique faux serial and verify that it is not used by any
    other asset in the repository. The length of the faux serial must be 4
    or greater.

    Returns a set of unique faux serials.
    """
    if length < 4:
        # 62^4 is ~14.7 million combinations. Which is the lowest acceptable
        # risk of collisions between independent checkouts of a repo.
        raise ValueError('The length of faux serial numbers must be >= 4.')

    if num < 1:
        raise ValueError('The length of faux serial numbers must be >= 1.')

    alphanum = string.ascii_letters + string.digits
    faux_serials = set()
    # Note: Here we are effectively accessing existing pseudo-keys via asset_files; The paths themselves are irrelevant.
    repo_faux_serials = {str(x.name).split('faux')[-1] for x in asset_files}

    while len(faux_serials) < num:
        serial = ''.join(random.choices(alphanum, k=length))
        if serial not in repo_faux_serials:
            faux_serials.add(f'faux{serial}')

    return faux_serials


def valid_asset_name(asset_file: Path) -> bool:
    """
    Verify that an asset name complies with the name scheme:
    <type>_<make>_<model>.<serial>
    Where the fields type, make, and model do not allow '.' or '_', serial
    permits all characters, and no field can be empty.

    Returns True for valid asset names, and False if invalid.
    """
    asset_file = Path(asset_file)

    try:
        re.findall(r'(^[^._]+?)_([^._]+?)_([^._]+?)\.(.+)', asset_file.name)[0]
    except (ValueError, IndexError):
        log.info(f"'{asset_file.name}' must be in the format '<type>_<make>_<model>.<serial>'")
        return False

    return True


def get_asset_files_by_path(asset_files: set[Path],
                            paths: Iterable[Path],
                            depth: Union[int, None]) -> list[Path]:
    """
    Check and normalize a list of paths. Select all assets in the
    repository that are relative to the given `paths` descending at most
    `depth` directories. A `depth` of 0 descends without a limit.
    """
    if depth and depth < 0:
        raise ValueError(f"depth values must be positive, but is {depth}.")

    paths = {Path(p) for p in paths}
    assets = [
        a for a in asset_files if any([
            a.is_relative_to(p) and
            (len(a.parents) - len(p.parents) <= depth if depth else True)
            for p in paths])]

    # Note: Why does this function need to raise instead of returning an empty list?
    #       The query yielded no matching asset. That's a valid response. What to do with that should be up to the
    #       caller.
    if not assets:
        raise ValueError('No assets selected.')

    return assets


def write_asset_file(asset_path: Path,
                     asset_content: Dict[str, Union[float, int, str]]) -> None:
    if asset_content == {}:
        asset_path.open('w').write("")
    else:
        yaml = YAML(typ='rt')
        yaml.dump(asset_content, asset_path)


def get_asset_content(asset_file: Path) -> Dict[str, Union[float, int, str]]:
    # asset_file: absolute

    yaml = YAML(typ='rt', pure=True)
    contents = dict()
    try:
        contents = yaml.load(asset_file)
    except scanner.ScannerError as e:
        print(e)
    if contents is None:
        return dict()
    return contents


def generate_new_asset_names(repo: OnyoRepo,
                             existing_asset_files: set[Path],
                             assets_to_set: list[Path],
                             name_values: Dict[str, Union[float, int, str]]) -> list[tuple[Path, Path]]:
    """
    Generate the pseudo key fields of an assets name (rename an asset file) from
    values of a dictionary and test that the new name is valid and
    available.
    Returns a list of tuples containing the mapping of old and new names or raises.
    """

    new_assets = []
    to_move = []

    # count and request the needed faux serial numbers
    faux_serial_list = []
    if 'serial' in name_values.keys() and name_values['serial'] == 'faux':
        faux_number = len(assets_to_set)
        if faux_number > 0:
            faux_serial_list = get_faux_serials(existing_asset_files, num=faux_number)

    for asset in assets_to_set:
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
            raise ValueError(f"New asset names must be different than old names: '{new_name}'")

        if not valid_asset_name(new_name):
            raise ValueError(f"New asset name is not valid: '{new_name}'")

        # God damnit. This check needs to go up:

        asset_path_available(repo, existing_asset_files, new_name, new_assets)
        new_assets.append(asset)
        to_move.append((asset, new_name))
    return to_move


def unset_asset_keys(asset: Path,
                     keys: list[str],
                     quiet: bool):
    # Note: This does not handle pseudo keys - see command_utils:unset
    contents = get_asset_content(asset)
    for field in keys:
        try:
            del contents[field]
        except KeyError:
            if not quiet:
                log.info(f"Field {field} does not exist in {asset}")
    write_asset_file(asset, contents)


def read_asset(asset):
    from .assets import get_asset_content
    return get_asset_content(asset)


def write_asset(asset: Path,
                contents: Dict[str, Union[float, int, str]]) -> None:
    from .assets import write_asset_file
    write_asset_file(asset, contents)


def read_assets_from_tsv(tsv: Path,
                         template_name: Optional[str],
                         key_values: Dict[str, str],
                         repo: OnyoRepo) -> Dict[Path, Dict[str, Union[float, int, str]]]:
    """
    Read a tsv table with a header row and one row for each new asset to
    create. Check the information (e.g. filenames correct and unique), and add
    faux serial numbers to the name if needed.

    Returns a dictionary with paths and contents of assets on success, or
    informs the user about missing or invalid information and exits with error.
    """
    new_assets = {}
    row_count = 0

    with tsv.open('r') as tsv_file:
        # count and request the faux serial numbers needed
        table = csv.DictReader(tsv_file, delimiter='\t')
        faux_number = sum([1 for row in table if row['serial'] == 'faux'])
        if faux_number > 0:
            faux_serial_list = get_faux_serials(repo.asset_paths, num=faux_number)

        # iterate over the table from the beginning to read asset information.
        tsv_file.seek(0)
        table = csv.DictReader(tsv_file, delimiter='\t')
        for row in table:
            row_count += 1
            new_path = ""
            contents = {}

            # error if any required field is empty
            if not all([row['type'], row['make'], row['model'], row['serial'], row['directory']]):
                row_str = "\t".join([value for value in row.values() if value])
                print(f"The fields 'type', 'make', 'model', 'serial' and 'directory' are required, but missing in line {row_count}: '{row_str}'", file=sys.stderr)
                sys.exit(1)

            # set asset name and directory, add faux serial numbers if needed
            if row['serial'] == 'faux':
                row['serial'] = faux_serial_list.pop()
            filename = f"{row['type']}_{row['make']}_{row['model']}.{row['serial']}"
            directory = row['directory']
            new_path = Path(repo.git.root, directory, filename).resolve()

            # verify that the asset name is valid and unique in repo and table
            asset_path_available(repo, repo.asset_paths, new_path, [*new_assets])

            # either a template is given in table, CLI, or onyo config
            template = None
            if "template" in row.keys():
                if row['template'] == "":
                    raise ValueError(f"Template value missing in {row_count}")
                template = repo.get_template_file(row['template'])
            elif template_name:
                template = repo.get_template_file(template_name)
            else:
                template = repo.get_template_file()

            # set the values from --keys and TSV columns, check for conflicts
            contents_valid = True
            contents = read_asset(template)
            if key_values:
                contents.update(key_values)
            for col in row.keys():
                # these fields contain meta information, not values for content
                if col in ['type', 'make', 'model', 'serial', 'directory', 'template']:
                    continue
                # information from --keys is not allowed to conflict with columns
                if key_values and col in key_values.keys():
                    print(f"Can't use --keys '{col}' and have tsv column '{col}'", file=sys.stderr)
                    contents_valid = False
                    break
                contents[col] = row[col]
            if not contents_valid:
                # Note: message missing. This was a plain sys.exit(1)
                raise ValueError

            new_assets[new_path] = contents

    return new_assets


def create_assets_in_destination(assets: Dict[Path, Dict[str, Union[float, int, str]]],
                                 repo: OnyoRepo) -> list[Path]:
    """
    Create and populate assets. Parent directories are created if necessary.
    """
    created_files = []
    for asset in assets.keys():
        # create missing directories
        if not asset.parent.exists():
            created_files.extend(repo.mk_inventory_dirs([asset.parent]))
        if not asset.is_file():
            asset.touch()
        write_asset(asset, assets[asset])
        created_files.append(asset)
    return created_files


def read_assets_from_CLI(assets: list[Path],
                         template_name: Optional[str],
                         key_values: Dict[str, str],
                         repo: OnyoRepo) -> Dict[Path, Dict[str, Union[float, int, str]]]:
    """
    Read information from `assets`, with a new asset file for each entry.
    Check the information (e.g. filename correct and unique), and add
    faux serial numbers to the names if needed.

    Returns a dictionary with paths and contents of assets on success, or
    informs the user about missing or invalid information and exits with error.
    """
    # Note: Optional declaration for `template_name` is misleading. It's being passed down from command implementation
    # where it is indeed optional, but in opposition to other params, it's invalid absence is only picked up in here
    # (via `get_template_file`, which raises)
    new_assets = {}

    # count and request the faux serial numbers needed
    faux_number = sum([1 for asset in assets if "faux" in asset.name.split('.')[-1]])
    if faux_number > 0:
        faux_serial_list = get_faux_serials(repo.asset_paths, num=faux_number)

    for asset in assets:
        new_path = ""
        contents = dict()

        # set paths
        if asset.name[-5:] == ".faux":
            new_name = asset.name[:-5] + asset.name[-5:].replace("faux", faux_serial_list.pop())
            new_path = asset.parent / new_name
        else:
            new_path = asset

        # verify that the asset name is valid and unique in repo and table
        asset_path_available(repo, repo.asset_paths, new_path, [*new_assets])

        # get template and check its existence and validity
        template = repo.get_template_file(template_name)

        # add values from --keys and template to asset:
        contents = read_asset(template)
        if key_values:
            contents.update(key_values)

        new_assets[new_path] = contents

    return new_assets


def get_assets_by_query(asset_files: set[Path],
                        keys: Set[str],
                        paths: Iterable[Path],
                        depth: Union[int, None] = None,
                        filters: Union[list[Filter], None] = None) -> Generator:
    """
    Get keys from assets matching paths and filters.
    """
    # Note: This is interested in the key-value pairs of assets, not their paths exactly.
    #       But tries to not read a file when pseudo keys are considered only

    # filter assets by path and depth relative to paths
    assets = get_asset_files_by_path(asset_files, paths, depth) or []

    if filters:
        # Filters that do not require loading an asset are applied first
        filters.sort(key=lambda x: x.is_pseudo, reverse=True)

        # Remove assets that do not match all filters
        for f in filters:
            assets[:] = filter(f.match, assets)

    # Obtain keys from remaining assets
    assets = ((a, {
        k: v
        for k, v in (get_asset_content(a) | dict(zip(
            PSEUDO_KEYS, re.findall(
                r'(^[^._]+?)_([^._]+?)_([^._]+?)\.(.+)',
                a.name)[0]))).items()
        if k in keys}) for a in assets)

    return assets


def asset_path_available(repo: OnyoRepo,
                         existing_asset_files: Set[Path],
                         asset: Path,
                         new_assets: list[Path]) -> None:
    """
    Test for an assets path and name if it can be used to create a new asset.
    """

    # Check Usage: First highlevel: have a valid name, then trigger lower-level "path available" or validation
    #  -> one level up (generate): Same story.

    if not valid_asset_name(asset):
        raise ValueError(f"'{asset}' is not a valid asset name.")
    # Note: Not clear why to go over all existing files; Path.exists() should suffice
    if file := [file for file in existing_asset_files if asset.name == file.name]:
        raise ValueError(f"Filename '{asset.name}' already exists as '{file[0]}'.")
    elif file := [file for file in new_assets if asset.name == file.name]:
        raise ValueError(f"Input contains multiple '{file[0].name}'")
    # Note: We already know it's a valid_asset_name and doesn't exist, so all that remains is:
    if not repo.is_inventory_path(asset):
        raise ValueError(f"The path is protected by onyo: '{asset}'")
