#!/usr/bin/env python3

import logging
import subprocess
from pathlib import Path
from typing import Optional, Union

from ruamel.yaml import YAML, scanner
from onyo.utils import (
    is_protected_path,
    validate_file
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

    #
    # FSCK
    #
    def fsck()
        """
        TODO:
        """
        # tests, list, etc


    def is_clean_tree(onyo_root, quiet):
        """
        Checks if the working tree for git is clean. Returns True or False.
        """
        repo = Repo(onyo_root)
        changed = [i.a_path for i in repo.index.diff(None)]
        staged = [i.a_path for i in repo.index.diff("HEAD")]
        untracked = repo.untracked_files

        if changed or staged or untracked:
            if not quiet:
                logger.error("The working tree is not clean.")

                if changed:
                    logger.error("Changes not staged for commit:")
                    logger.error('\n\t' + '\n\t'.join(changed))

                if staged:
                    logger.error("Changes to be committed:")
                    logger.error('\n\t' + '\n\t'.join(staged))

                if untracked:
                    logger.error("Untracked files:")
                    logger.error('\n\t' + '\n\t'.join(untracked))

                logger.error("Please commit all changes or add untracked files to .gitignore")

            return False

        return True

    def verify_anchors(onyo_root, quiet):
        """
        Checks if all dirs (except those in .onyo) contain an .anchor file.
        Returns True or False.
        """
        # anchors in repo
        anchors_exist = {x[0][0] for x in Repo(onyo_root).index.entries.items()
                         if Path(x[0][0]).name == '.anchor' and
                         '.onyo' not in Path(x[0][0]).parts}

        # anchors that should exist
        anchors_expected = {'{}/.anchor'.format(x.relative_to(onyo_root)) for x in Path(onyo_root).glob('**/')
                            if not is_protected_path(x) and
                            not x.samefile(onyo_root)}

        # are any missing
        difference = anchors_expected.difference(anchors_exist)

        if difference:
            if not quiet:
                logger.error('The following .anchor files are missing:')
                logger.error('\n'.join(difference))
                logger.error("Likely 'mkdir' was used to create the directory. Use 'onyo mkdir' instead.")
                # TODO: Prompt the user if they want Onyo to fix it.

            return False

        return True

    def verify_yaml(onyo_root, quiet):
        """
        Checks if all assets have valid YAML. Returns True or False.
        """
        invalid_yaml = []

        for asset in get_list_of_assets(onyo_root):
            # TODO: use valid_yaml()
            try:
                YAML().load(Path(onyo_root, asset))
            except scanner.ScannerError:
                invalid_yaml.append(asset)

        if invalid_yaml:
            if not quiet:
                logger.error('The following files fail YAML validation:')
                logger.error('\n'.join(invalid_yaml))

            return False

        return True

    def verify_unique_file_names(onyo_root, quiet):
        """
        Checks if all files have unique names. Returns True or False.
        """
        # TODO: this checks all files. This should only check /assets/.
        files = {x[0][0] for x in Repo(onyo_root).index.entries.items()
                 if not is_protected_path(x[0][0])}
        filenames = {}
        for f in files:
            try:
                filenames[Path(f).name].append(f)
            except KeyError:
                filenames[Path(f).name] = [f]

        if len(files) != len(filenames):
            if not quiet:
                logger.error('The following file names are not unique:')
                logger.error('\n'.join([x for x in filenames
                                        if len(filenames[x] > 1)]))

            return False

        return True

    def validate_assets(onyo_root, quiet):
        """
        Checks if all assets pass validation. Returns True or False.
        """
        invalid = {}
        for asset in get_list_of_assets(onyo_root):
            msg = validate_file(asset, asset, onyo_root)
            if msg:
                invalid[asset] = msg

        if invalid:
            if not quiet:
                logger.error('The contents of the following files fail validation:')
                logger.error('\n'.join([f'{x}\n{invalid[x]}' for x in invalid]))

            return False

        return True
