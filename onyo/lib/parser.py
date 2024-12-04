from pathlib import Path

from onyo.lib.inventory import OPERATIONS_MAPPING


def parse_operations_record(record: list[str]) -> dict:

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
                if not collecting_key or line and not line.startswith("- "):
                    raise RuntimeError("Invalid operations record.")
                cleaned_line = line[2:].split(" -> ")
                if len(cleaned_line) > 2:
                    raise RuntimeError(f"Invalid operations record:{line}")
                if len(cleaned_line) == 1:
                    parsed_record[collecting_key].append(Path(cleaned_line[0]))
                else:
                    parsed_record[collecting_key].append(
                        (Path(cleaned_line[0]), Path(cleaned_line[1]))
                    )
    return parsed_record
