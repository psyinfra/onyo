from pathlib import Path
from typing import Dict, Iterable, Union

from ruamel.yaml import YAML, scanner  # pyre-ignore[21]

from .onyo import Repo, log


def is_protected_path(path: Union[Path, str]) -> bool:
    """
    Checks whether a path contains protected elements (.anchor, .git, .onyo).
    Returns True if it contains protected elements. Otherwise False.
    """
    full_path = Path(path).resolve()

    # protected paths
    for p in full_path.parts:
        if p in ['.anchor', '.git', '.onyo']:
            return True

    return False


def get_assets(repo: Repo) -> set[Path]:
    # TODO: make if asset-style name (i.e. README won't match)
    # TODO: check for .onyoignore
    assets = {x for x in repo.files if not is_protected_path(x)}
    return assets


def get_templates(repo: Repo) -> set[Path]:
    return {repo.sanitize_path(file)
            for file in Path(repo.root, ".onyo", "templates").glob('*')
            if Path(file).is_file() and not Path(file).name == ".anchor"}


def read_asset(asset):
    yaml = YAML(typ='rt', pure=True)
    contents = dict()
    try:
        contents = yaml.load(asset)
    except scanner.ScannerError as e:
        print(e)
    if contents is None:
        return dict()
    return contents


def get_assets_by_path(repo: Repo, paths: Iterable[Union[Path, str]],
                       depth: Union[int, None]) -> list[Path]:
    if depth and depth < 0:
        log.error(f"depth values must be positive, but is {depth}.")
        raise ValueError(f"depth values must be positive, but is {depth}.")

    paths = {repo.sanitize_path(p) for p in paths}
    assets = [
        a for a in repo.assets if any([
            a.is_relative_to(p) and
            (len(a.parents) - len(p.parents) <= depth if depth else True)
            for p in paths])]

    if not assets:
        msg = 'No assets selected.'
        log.error(msg)
        raise ValueError(msg)

    return assets


def write_asset(asset: Path,
                contents: Dict[str, Union[float, int, str]]) -> None:
    if contents == {}:
        asset.open('w').write("")
    else:
        yaml = YAML(typ='rt')
        yaml.dump(contents, asset)
