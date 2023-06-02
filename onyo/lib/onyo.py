import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union

from .git import GitRepo
from .exceptions import OnyoInvalidRepoError, OnyoProtectedPathError

log: logging.Logger = logging.getLogger('onyo.onyo')


class OnyoRepo(object):

    ONYO_DIR = Path('.onyo')
    TEMPLATE_DIR = 'templates'
    ANCHOR_FILE = '.anchor'

    def __init__(self,
                 path: Path,
                 init: bool = False,
                 find_root: bool = False):
        """
        Instantiates a `OnyoRepo` object with `path` as the root directory.

        If `find_root=True` searches the root of a repository from `path`.

        If `init=True`, the `path` will be initialized as a git repo and a
        `.onyo/` directory will be created. `find_root=True` must not be used
        in combination with `init=True`.
        Otherwise the validity of the onyo repository is verified, and if the
        path is invalid a `OnyoInvalidRepoError` is raised.
        """
        self.git = GitRepo(path, find_root=find_root)
        self.dot_onyo = self.git.root / self.ONYO_DIR

        if init:
            if find_root:
                raise ValueError("`find_root=True` must not be used with `init=True`")
            self._init(path)
        else:
            if not self.is_valid_onyo_repo():
                raise OnyoInvalidRepoError(f"'{path}' is no valid Onyo Repository.")

        log.debug(f"Onyo repo found at '{self.git.root}'")

        # caches
        self._asset_paths: Union[set[Path], None] = None

    def clear_caches(self, assets: bool = True) -> None:
        """
        Clear caches of the instance of the repository object.

        Paths such as files, assets, and directories are cached, and can become
        stale when the repository contents are modified. This function clears
        the caches of the properties.

        By default all caches are cleared, and arguments make it possible to
        specify which caches which should remain set.

        If the repository is exclusively modified via public API functions, the
        caches of the `Repo` object are consistent. If the repository is
        modified otherwise, this function clears the caches to ensure that the
        caches do not contain stale information.
        """
        if assets:
            self._asset_paths = None
            self.git.clear_caches(files=True)

    def generate_commit_message(self,
                                message: Union[list[str], None] = None,
                                cmd: str = "",
                                keys: Union[list[str], None] = None,
                                destination: str = "",
                                max_length: int = 80,
                                modified: Optional[list[Path]] = None) -> str:
        """
        Generate a commit subject and body suitable for use with git commit.

        If `message` is given, the function uses the first element of it to
        generate a message subject, and the following ones are joined for the
        message body.

        If no `message` is given, generate a default commit message based on
        the other parameters given, and the `files staged` in the repository.
        The paths for the message are shortened if needed, so that the resulting
        message subject does not exceed `MAX_LEN`.

        Adds a list of changed files with their path relative to the root of
        the repository to the body of all commit messages. This is based on the
        `modified` parameter or on currently staged paths if none was given.
        """
        message = [] if message is None else message
        keys = [] if keys is None else keys
        if modified is None:
            modified = self.git.files_staged

        message_subject = ""
        message_body = ""
        message_appendix = ""

        # staged files and directories (without ".anchor") in alphabetical order
        changes_to_record = [x if not x.name == self.ANCHOR_FILE else x.parent
                             for x in sorted(f.relative_to(self.git.root) for f in modified)]

        if message:
            message_subject = message[0][0]
            message_body = '\n'.join(map(str, [x[0] for x in message[1:]]))
        else:
            # get variables for the begin of the commit message `msg_dummy`
            dest = None
            keys_str = ""
            if keys:
                keys_str = f" ({','.join(str(x.split('=')[0]) for x in sorted(keys))})"
            if destination:
                # Note: This seems to expect relative path in `destination`, turns it into absolute and
                #       back into relative. Double-check where `destination` is used and remove resolution:
                dest = Path(self.git.root, destination).relative_to(self.git.root)
            if dest and dest.name == self.ANCHOR_FILE:
                dest = dest.parent

            # the `msg_dummy` is the way all automatically generated commit
            # message headers (independently of later adding/shortening of
            # information) begin, for all commands.
            msg_dummy = f"{cmd} [{len(changes_to_record)}]{keys_str}"
            message_subject = self._generate_commit_message_subject(
                msg_dummy, changes_to_record, dest, max_length)

        message_appendix = '\n'.join(map(str, changes_to_record))
        return f"{message_subject}\n\n{message_body}\n\n{message_appendix}"

    @staticmethod
    def _generate_commit_message_subject(
            msg_dummy: str, changes: list[Path],
            destination: Optional[Path], max_length: int = 80) -> str:
        """
        Generates "commit message subject" with the `msg_dummy` and the paths
        from `staged_changes` and `destination`, and shortens the paths if the
        message length exceeds the `MAX_LEN`.
        """

        # long message: full paths (relative to repo-root)
        paths_str = ','.join([f"'{x}'" for x in changes])
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination}'"

        if len(msg) < max_length:
            return msg

        # medium message: highest level (e.g. dir or asset name)
        paths = [x.name for x in changes]
        paths_str = ','.join(["'{}'".format(x) for x in paths])
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination.relative_to(destination.parent)}'"

        if len(msg) < max_length:
            return msg

        # short message: "type" of devices in summary (e.g.  "laptop (2)")
        paths = [x.name.split('_')[0] for x in changes]
        paths_str = ','.join(sorted(["'{} ({})'".format(x, paths.count(x))
                                     for x in set(paths)]))
        msg = f"{msg_dummy}: {paths_str}"
        if destination:
            msg = f"{msg} -> '{destination.relative_to(destination.parent)}'"

        # return the shortest possible version of the commit message as fallback
        return msg

    @property
    def asset_paths(self) -> set[Path]:
        """
        A `set` containing the absolute `Path`s of all assets of a repository.

        This property is cached, and the cache is consistent with the state of
        the repository when only `OnyoRepo`s public functions are used. Use of
        private functions might require a manual reset of the caches, see
        `OnyoRepo.clear_caches()`.
        """
        if self._asset_paths is None:
            self._asset_paths = self.get_asset_paths()
        return self._asset_paths

    def is_valid_onyo_repo(self) -> bool:
        """
        Assert whether this is a properly set up onyo repository and has a fully
        populated `.onyo/` directory.
        """
        files = ['config',
                 OnyoRepo.ANCHOR_FILE,
                 Path(OnyoRepo.TEMPLATE_DIR) / OnyoRepo.ANCHOR_FILE,
                 Path('validation') / OnyoRepo.ANCHOR_FILE]

        # has expected .onyo structure
        if not all(x.is_file() for x in [self.dot_onyo / f for f in files]):
            return False

        # is a git repository
        if subprocess.run(["git", "rev-parse"],
                          cwd=self.git.root,
                          stdout=subprocess.DEVNULL).returncode != 0:
            return False
        return True

    def _init(self, path: Path) -> None:
        """Initialize an Onyo repository at `path`

        The directory will be initialized as a git repository (if it is not one already),
        ``.onyo/`` directory created (containing default config files, templates, etc.),
        and everything committed.

        Re-init-ing an existing repository is safe. It will not overwrite
        anything; it will raise an exception.
        """

        # Note: Why is this necessary to check? Assuming we call git-init on it,
        # this will repeat that same test anyway (and would fail telling us this problem)
        # target must be a directory
        if path.exists() and not path.is_dir():
            raise FileExistsError(f"'{path}' exists but is not a directory.")

        # Note: Why is this a requirement? What could go wrong with mkdir-p ?
        # parent must exist
        if not path.parent.exists():
            raise FileNotFoundError(f"'{path.parent}' does not exist.")

        # Note: Why is this a requirement? Why not only add what's missing in case of apparent re-init?
        # cannot already be an .onyo repo
        dot_onyo = Path(path, '.onyo')
        if dot_onyo.exists():
            raise FileExistsError(f"'{dot_onyo}' already exists.")

        self.git.maybe_init(path)

        # Note: pheewww - No. Installed resource needs to be found differently.
        #       Who the hell is supposed to maintain that? One cannot simply move
        #       this function without changing its implementation.
        skel_dir = Path(Path(__file__).resolve().parent.parent, 'skel')

        # populate .onyo dir
        shutil.copytree(skel_dir, self.dot_onyo)

        # add and commit
        self.git.stage_and_commit(self.dot_onyo, message='Initialize as an Onyo repository')
        log.info(f'Initialized Onyo repository in {self.dot_onyo}/')

    def is_onyo_path(self, path: Path) -> bool:
        return path == self.dot_onyo or self.dot_onyo in path.parents or path.name.startswith('.onyo')  # see .onyoignore

    def is_inventory_dir(self, path: Path) -> bool:
        # - existing inventory directory
        # - includes repo.root as "root location"  --> is this valid?
        # Note: This currently ignores whether there's tracked content in that dir
        return self.is_inventory_path(path) and path.is_dir()

    def is_asset_path(self, path: Path) -> bool:
        # TODO: check for .onyoignore
        # TODO: possibly nested assets; hence "asset path", not "asset file"
        # TODO: We are currently ignoring .gitignore w/ underlying globbing
        return self.is_inventory_path(path) and \
            path.is_file()

    def is_inventory_path(self, path: Path) -> bool:
        # Note: path underneath an inventory location with no regard for existence of `path` itself.
        #       This is still a little ugly, since is_inventory_dir is amost identical. Trouble comes from
        #       root being an inventory dir. Consider lru_cache for these checks. Dependency is_inventory_dir vs *_path
        #       seems wrong. Things change when we know the path exists, because in case of a file there's another
        #       restriction (ANCHOR)
        return path.is_relative_to(self.git.root) and \
            not self.git.is_git_path(path) and \
            not self.is_onyo_path(path) and \
            self.ANCHOR_FILE not in path.parts

    def get_template_file(self, name: Union[Path, str, None] = None) -> Path:
        """
        Select the template to use. If no template name is given, use the
        template from the repository config file `.onyo/config`.

        Returns the template path on success, or raises `ValueError`.
        """
        if not name:
            name = self.git.get_config('onyo.new.template')
            if name is None:
                raise ValueError("Either --template must be given or 'onyo.new.template' must be set.")

        # Note: Protect against providing absolute path in `template_name`?
        template_file = self.git.root / self.ONYO_DIR / self.TEMPLATE_DIR / name
        if not template_file.is_file():
            raise ValueError(f"Template {name} does not exist.")
        return template_file

    def validate_anchors(self) -> bool:
        """
        Check if all dirs (except those in .onyo) contain an .anchor file.
        Returns True or False.
        """
        # Note: First line not using protected_paths, because `.anchor` is part of it.
        #       But ultimately, exist vs expected should take the same subtrees into account. So - not good to code it
        #       differently.
        anchors_exist = {x
                         for x in self.git.files
                         if x.name == self.ANCHOR_FILE and
                         not self.is_onyo_path(x)}

        anchors_expected = {x.joinpath(self.ANCHOR_FILE)
                            for x in [self.git.root / f for f in self.git.root.glob('**/')]
                            if self.is_inventory_dir(x) and not x == self.git.root}
        difference = anchors_expected.difference(anchors_exist)

        if difference:
            log.warning(
                'The following .anchor files are missing:\n'
                '{0}'.format('\n'.join(map(str, difference))))
            log.warning(
                "Likely 'mkdir' was used to create the directory. Use "
                "'onyo mkdir' instead.")
            # TODO: Prompt the user if they want Onyo to fix it.

            return False

        return True

    def get_asset_paths(self) -> set[Path]:
        # TODO: make if asset-style name (i.e. README won't match)

        # Note: Why the hell suddenly use repo.files? This is so inconsistent ...
        # actual asset files
        assets = {x for x in self.git.files if self.is_asset_path(x)}
        return assets

    def mk_inventory_dirs(self, dirs: Union[Iterable[Path], Path]):
        if isinstance(dirs, Path):
            dirs = [dirs]
        non_inventory_paths = [d for d in dirs if not self.is_inventory_path(d)]
        if non_inventory_paths:
            raise OnyoProtectedPathError(
                'The following paths are protected by onyo:\n{}\nNo '
                'directories were created.'.format(
                    '\n'.join(map(str, non_inventory_paths))))

        # Note: This check is currently done here, because we are dealing with a bunch of directories at once.
        #       We may want to operate on single dirs, rely on mkdir throwing instead, and collect errors higher up.
        file_paths = [d for d in dirs if d.is_file()]
        if file_paths:
            raise FileExistsError(
                'The following paths are existing files:\n{}\nNo directories were '
                'created.'.format(
                    '\n'.join(map(str, file_paths))))

        # make dirs
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # anchors
        anchors = {i / OnyoRepo.ANCHOR_FILE for d in dirs
                   for i in [d] + list(d.parents)
                   if i.is_relative_to(self.git.root) and
                   not i.samefile(self.git.root)}
        for a in anchors:
            a.touch(exist_ok=True)

        self.git.stage(anchors)
