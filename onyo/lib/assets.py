from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional, Set

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo.lib.ui import ui
from onyo.lib.utils import get_asset_content

log: logging.Logger = logging.getLogger('onyo.assets')


def contains_no_name_keys(asset_files: Set[Path]) -> bool:
    # Note: This actually operates on content, not on files/paths
    # TODO: This is probably the last place using the old NAME_KEYS
    #       as hte ones whose values are only stored in asset names.
    #       Fix in context of `fsck`.
    NAME_KEYS = ["type", "make", "model", "serial"]
    assets_failed = {}

    for asset in asset_files:
        violation_list = [
            x for x in NAME_KEYS if x in get_asset_content(asset)]
        if violation_list:
            assets_failed[asset] = violation_list

    if assets_failed:
        ui.error(
            "The keys {0} are reserved for asset file names, and are "
            "not allowed in the asset's contents. The following assets "
            "contain asset name keys:\n{1}".format(
                tuple(NAME_KEYS),
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
        ui.error('The following file names are not unique:\n{}'.format(
            '\n'.join(map(str, duplicates))))
        return False

    return True


def validate_assets(asset_files: Set[Path]) -> bool:
    invalid = {}
    for asset in asset_files:
        # TODO: validate assets
        pass

    if invalid:
        ui.error(
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
        ui.error('The following files fail YAML validation:\n{}'.format(
            '\n'.join(invalid_yaml)))

        return False

    return True


def get_asset_files_by_path(asset_files: list[Path],
                            paths: Iterable[Path],
                            depth: Optional[int]) -> list[Path]:
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


# The idea of an Asset class is currently abandoned. If not re-introduced, can go entirely.
# It would, however, be a dict-like in any case (prob. derived from UserDict, though)
Asset = dict
