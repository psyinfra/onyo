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

# TODO: Most functions here account for asset being given as dict or Path.
#       This is probably superfluous. Re-evaluate, when the `Inventory` class
#       is reasonably stable.


def record_item(repo: OnyoRepo, item: Path | dict) -> str:
    path = item if isinstance(item, Path) else item['path']
    return f"- {path.relative_to(repo.git.root).as_posix()}\n"


def record_move(repo: OnyoRepo, src: Path | dict, dst: Path) -> str:
    # This currently expects `dst` to be the dir to move src into,
    # rather than already containing src' name at the destination.
    src_path = src if isinstance(src, Path) else src['path']
    dst_path = (dst / src_path.name).relative_to(repo.git.root).as_posix()
    src_path = src_path.relative_to(repo.git.root).as_posix()
    return f"- {src_path} -> {dst_path}\n"


def record_rename(repo: OnyoRepo, src: Path | dict, dst: Path) -> str:
    # In opposition to record_move, this expects the full target path in `dst`
    src_path = src if isinstance(src, Path) else src['path']
    src_path = src_path.relative_to(repo.git.root).as_posix()
    dst_path = dst.relative_to(repo.git.root).as_posix()
    return f"- {src_path} -> {dst_path}\n"


def record_new_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {"New assets:\n": [record_item(repo, operands[0])]}


def record_new_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {"New directories:\n": [record_item(repo, operands[0])]}


def record_remove_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {"Removed assets:\n": [record_item(repo, operands[0])]}


def record_remove_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {"Removed directories:\n": [record_item(repo, operands[0])]}


def record_move_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    records = {"Moved assets:\n": [record_move(repo, operands[0], operands[1])]}
    if repo.is_asset_dir(operands[0]):
        # In case of an asset dir, we need to record an operation for both aspects
        records.update({"Moved directories:\n": [record_move(repo, operands[0], operands[1])]})
    return records


def record_move_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    records = {"Moved directories:\n": [record_move(repo, operands[0], operands[1])]}
    if repo.is_asset_dir(operands[0]):
        # In case of an asset dir, we need to record an operation for both aspects
        records.update({"Moved assets:\n": [record_move(repo, operands[0], operands[1])]})
    return records


def record_rename_directories(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {"Renamed directories:\n": [record_rename(repo, operands[0], operands[1])]}


def record_rename_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    records = {"Renamed assets:\n": [record_rename(repo, operands[0], operands[1])]}
    if repo.is_asset_dir(operands[0]):
        # In case of an asset dir, we need to record an operation for both aspects
        records.update({"Renamed directories:\n": [record_rename(repo, operands[0], operands[1])]})
    return records


def record_modify_assets(repo: OnyoRepo, operands: tuple) -> dict[str, list[str]]:
    return {"Modified assets:\n": [record_item(repo, operands[0])]}
