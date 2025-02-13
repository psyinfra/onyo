from pathlib import Path

from onyo.lib.inventory import OPERATIONS_MAPPING


def parse_operations_record(record: list[str]) -> dict:
    r"""Parse a textual Inventory Operations record.

    To extract a collection of Inventory Operations from a git commit message.

    Each field of the returned dict is a list of Paths or Path pairs.
    """

    if not record[0].strip() == "--- Inventory Operations ---":
        raise RuntimeError("Invalid operations record.")

    parsed_record = {k: [] for k in OPERATIONS_MAPPING.keys()}
    collecting_key = None
    for line in record[1:]:
        line = line.strip()
        if not line:
            continue
        match line:
            case "New assets:":
                collecting_key = "new_assets"
            case "New directories:":
                collecting_key = "new_directories"
            case "Removed assets:":
                collecting_key = "remove_assets"
            case "Removed directories:":
                collecting_key = "remove_directories"
            case "Moved assets:":
                collecting_key = "move_assets"
            case "Moved directories:":
                collecting_key = "move_directories"
            case "Renamed directories:":
                collecting_key = "rename_directories"
            case "Renamed assets:":
                collecting_key = "rename_assets"
            case "Modified assets:":
                collecting_key = "modify_assets"
            case _:
                if not collecting_key:
                    raise RuntimeError("Invalid operations record.")
                if collecting_key and not line.startswith("- "):
                    raise RuntimeError("Invalid operations record.")

                clean_line = line.removeprefix('- ').split(" -> ")
                match len(clean_line):
                    case 1:
                        parsed_record[collecting_key].append(Path(clean_line[0]))
                    case 2:
                        parsed_record[collecting_key].append(
                            (Path(clean_line[0]), Path(clean_line[1]))
                        )
                    case _:
                        raise RuntimeError(f"Invalid operations record:{line}")

    return parsed_record
