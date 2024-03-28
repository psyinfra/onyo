from __future__ import annotations

import logging
from pathlib import Path
from typing import Set

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from onyo.lib.ui import ui

log: logging.Logger = logging.getLogger('onyo.assets')


def has_unique_names(asset_files: Set[Path]) -> bool:
    asset_names = [a.name for a in asset_files]
    duplicates = [a for a in asset_files if asset_names.count(a.name) > 1]
    duplicates.sort(key=lambda x: x.name)

    if duplicates:
        ui.error('The following file names are not unique:\n{}'.format(
            '\n'.join(map(str, duplicates))))
        return False

    return True


def validate_yaml(asset_files: list[Path] | None) -> bool:
    # Note: Does not (and cannot) account for asset dirs automatically in this form.
    #       Thus needs to be done by caller.
    # Note: assumes absolute paths!
    invalid_yaml = []
    asset_files = asset_files or []
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


# The idea of an Asset class is currently abandoned. If not re-introduced, can go entirely.
# It would, however, be a dict-like in any case (prob. derived from UserDict, though)
Asset = dict
