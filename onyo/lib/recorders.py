from os import linesep
from pathlib import Path

from onyo.lib.onyo import OnyoRepo

# Recorders signature: (repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]
# Returned dict: {<title for operations record section>: [<snippet recording concrete operation>, ..]
#
# This is meant to result in a commit message footer composed by `Inventory.commit()`:
#
# --- Inventory Operations ---
# <title for operations record section>:
#   <snippet recording concrete operation>
#   <snippet recording concrete operation>
# <title for operations record section>:
#   <snippet recording concrete operation>
#   <snippet recording concrete operation>
#
# While a recorder currently only ever returns a single snippet (line) for an operation,
# the dict assumes a list in order to provide the option to deliver several.

# TODO: Double-check we always report posix paths!


def record_item(repo: OnyoRepo, item: Path | dict) -> str:
    path = item if isinstance(item, Path) else item['path']
    return f"- {path.relative_to(repo.git.root).as_posix()}{linesep}"


def record_move(repo: OnyoRepo, src: Path | dict, dst: Path) -> str:
    # Attention: This currently expects `dst` to be the dir to move src into,
    # rather than already containing src' name at the destination. This may not be consistent yet.
    src_path = src if isinstance(src, Path) else src['path']
    dst_path = (dst / src_path.name).relative_to(repo.git.root).as_posix()
    src_path = src_path.relative_to(repo.git.root).as_posix()
    return f"- {src_path} -> {dst_path}{linesep}"


def record_new_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"New assets:{linesep}": [record_item(repo, operands[0])]}


def record_new_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"New directories:{linesep}": [record_item(repo, operands[0])]}


def record_remove_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"Removed assets:{linesep}": [record_item(repo, operands[0])]}


def record_remove_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"Removed directories:{linesep}": [record_item(repo, operands[0])]}


def record_move_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"Moved assets:{linesep}": [record_move(repo, operands[0], operands[1])]}


def record_move_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"Moved directories:{linesep}": [record_move(repo, operands[0], operands[1])]}


def record_rename_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"Renamed directories:{linesep}": [record_move(repo, operands[0], operands[1])]}


def record_rename_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    # TODO: This needs a special case for asset dirs. Record both - an
    # asset renamed and a directory renamed. This cannot be addressed by an
    # actual rename directory operation being executed and then recorded, because renaming
    # of asset depends on content and config. (Plus: We can't actually rename the same thing twice)
    #
    # This type of double recording may need to be done for other operations on asset dirs - double-check!
    return {f"Renamed assets:{linesep}": [record_move(repo, operands[0], operands[1])]}


def record_modify_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {f"Modified assets:{linesep}": [record_item(repo, operands[0])]}
