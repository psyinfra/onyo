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
    def fsck(self, tests: list = None, quiet: bool = True, quiet_tests: bool = False) -> bool:
        """
        Run a suite of checks to verify the integrity and validity of an Onyo
        repository and its contents.

        By default, the following tests will be performed:

        - "clean-tree": verifies that the git tree is clean ---that there are
          no changed (staged or unstaged) nor untracked files.
        - "anchors": verifies that all folders (outside of .onyo) have an
          .anchor file
        - "asset-unique": verifies that all asset names are unique
        - "asset-yaml": loads each assets and checks if it's valid YAML
        - "asset-validity": loads each asset and validates the contents against
          the validation rulesets defined in ``.onyo/validation/validation.yaml``.
        """
        all_tests = {
            "clean-tree": self._fsck_clean_tree,
            "anchors": self._fsck_anchors,
            "asset-unique": self._fsck_unique_assets,
            "asset-yaml": self._fsck_yaml,
            "asset-validity": self._fsck_validation,
        }
        if tests:
            # only known tests are accepted
            if [x for x in tests if x not in all_tests.keys()]:
                raise ValueError("Invalid test requested. Valid tests are: {}".format(', '.join(all_tests.keys())))
        else:
            tests = all_tests.keys()

        # run the selected tests
        for key in tests:
            if not quiet:
                print(f"running '{key}' ... ", end='', flush=True)

            if not all_tests[key](quiet_tests):
                if not quiet:
                    print("failed")

                raise InvalidOnyoRepoError(f"'{self._opdir}' failed fsck test '{key}'")

            if not quiet:
                print("succeeded")

        return True

    def _fsck_anchors(self, quiet: bool = False) -> bool:
        """
        Check if all dirs (except those in .onyo) contain an .anchor file.
        Returns True or False.
        """
        anchors_exist = {x for x in self.files if x.name == '.anchor' and '.onyo' not in x.parts}
        anchors_expected = {x.joinpath('.anchor') for x in self.dirs
                            if not is_protected_path(x)}
        difference = anchors_expected.difference(anchors_exist)

        if difference:
            if not quiet:
                log.error('The following .anchor files are missing:')
                log.error('\n'.join(difference))
                log.error("Likely 'mkdir' was used to create the directory. Use 'onyo mkdir' instead.")
                # TODO: Prompt the user if they want Onyo to fix it.

            return False

        return True

    def _fsck_clean_tree(self, quiet: bool = False) -> bool:
        """
        Check if the working tree for git is clean. Returns True or False.
        """
        changed = [x for x in self._git(['diff', '--name-only']).split('\n') if x]
        staged = [x for x in self._git(['diff', '--name-only', '--staged']).split('\n') if x]
        untracked = [x for x in self._git(['ls-files', '--others', '--exclude-standard']).split('\n') if x]

        if changed or staged or untracked:
            if not quiet:
                log.error("The working tree is not clean.")

                if changed:
                    log.error("Changes not staged for commit:")
                    log.error('\n\t' + '\n\t'.join(changed))

                if staged:
                    log.error("Changes to be committed:")
                    log.error('\n\t' + '\n\t'.join(staged))

                if untracked:
                    log.error("Untracked files:")
                    log.error('\n\t' + '\n\t'.join(untracked))

                log.error("Please commit all changes or add untracked files to .gitignore")

            return False

        return True

    def _fsck_unique_assets(self, quiet: bool = False) -> bool:
        """
        Check if all files have unique names. Returns True or False.
        """
        names = {}
        for f in self.assets:
            try:
                names[f.name].append(f)
            except KeyError:
                names[f.name] = [f]

        if len(self.assets) != len(names):
            if not quiet:
                log.error('The following file names are not unique:')
                log.error('\n'.join([str(x) for x in names
                                     if len(names[x] > 1)]))

            return False

        return True

    def _fsck_validation(self, quiet: bool = False) -> bool:
        """
        Check if all assets pass validation. Returns True or False.
        """
        invalid = {}
        for asset in self.assets:
            # TODO: check if this still works
            msg = validate_file(asset, asset, self.root)
            if msg:
                invalid[asset] = msg

        if invalid:
            if not quiet:
                log.error('The contents of the following files fail validation:')
                log.error('\n'.join([f'{x}\n{invalid[x]}' for x in invalid]))

            return False

        return True

    def _fsck_yaml(self, quiet: bool = False) -> bool:
        """
        Check if all assets have valid YAML. Returns True or False.
        """
        invalid_yaml = []

        for asset in self.assets:
            # TODO: use valid_yaml()
            try:
                YAML().load(Path(self.root, asset))
            except scanner.ScannerError:
                invalid_yaml.append(asset)

        if invalid_yaml:
            if not quiet:
                log.error('The following files fail YAML validation:')
                log.error('\n'.join([str(x) for x in invalid_yaml]))

            return False

        return True
