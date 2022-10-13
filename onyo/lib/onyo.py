#!/usr/bin/env python3

import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

from onyo.utils import (
    is_protected_path
)

logging.basicConfig()
log = logging.getLogger('onyo')


class InvalidOnyoRepoError(Exception):
    """Thrown if the repository is invalid."""


class Repo:
    """
    """
    def __init__(self, path: Union[Path, str]) -> None:
        self._opdir = Path(path).resolve()
        self._root = self._get_root()
        # caches
        self._assets = None
        self._dirs = None
        self._files = None
        self._gitfiles = None

    @property
    def assets(self) -> set[Path]:
        if not self._assets:
            self._assets = self._get_assets()

        return self._assets

    @property
    def dirs(self) -> set[Path]:
        if not self._dirs:
            self._dirs = self._get_dirs()

        return self._dirs

    @property
    def files(self) -> set[Path]:
        if not self._files:
            self._files = self._get_files()

        return self._files

    @property
    def opdir(self) -> Path:
        return self._opdir

    @property
    def root(self) -> Path:
        return self._root

    def _get_assets(self) -> set[Path]:
        """
        Return a set of all assets in the repository.
        """
        assets = {x for x in self.files if not is_protected_path(x)}

        # TODO: make if asset-style name (i.e. README won't match)
        # TODO: check for .onyoignore

        return assets

    def _get_dirs(self) -> set[Path]:
        """
        Return a set of all directories in the repository (except under .git).
        """
        dirs = {x.relative_to(self.root) for x in Path(self.root).glob('**/')
                if '.git' not in x.parts and
                not x.samefile(self.root)}

        return dirs

    def _get_files(self) -> set[Path]:
        """
        Return a set of all files in the repository (except under .git).
        """
        files = {Path(x) for x in self._git(['ls-files']).split('\n') if x}
        return files

    def _get_root(self) -> Path:
        """
        """
        try:
            root = self._git(['rev-parse', '--show-toplevel'], cwd=self._opdir).strip()
        except subprocess.CalledProcessError:
            log.error(f"'{self._opdir}' is not a Git repository.")
            raise InvalidOnyoRepoError(f"'{self._opdir}' is not a Git repository.")

        root = Path(root)
        if not Path(root, '.onyo').is_dir():
            log.error(f"'{root}' is not an Onyo repository.")
            raise InvalidOnyoRepoError(f"'{self._opdir}' is not an Onyo repository.")

        # TODO: check .onyo/config, etc

        return root

    #
    # _git
    #
    def _git(self, args: list[str], *, cwd: Optional[Path] = None, raise_error: bool = True) -> str:
        """
        """
        if cwd is None:
            cwd = self.root

        ret = subprocess.run(["git"] + args,
                             cwd=cwd, check=raise_error,
                             capture_output=True, text=True)

        return ret.stdout
