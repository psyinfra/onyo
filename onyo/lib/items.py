from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import CommentedMap  # pyre-ignore[21]

import onyo.lib.onyo
import onyo.lib.inventory
import onyo.lib.pseudokeys
from onyo.lib.utils import DotNotationWrapper


if TYPE_CHECKING:
    from typing import (
        Any,
        Mapping,
        TypeVar,
    )

    _KT = TypeVar("_KT")  # Key type
    _VT = TypeVar("_VT")  # Value type


def resolve_alias(key: Any) -> Any:
    """Return the target key of a key alias."""

    try:
        return onyo.lib.pseudokeys.PSEUDOKEY_ALIASES[key]
    except KeyError:
        return key


class Item(DotNotationWrapper):
    """An item that an :py:class:`onyo.lib.inventory.Inventory` can potentially track.

    The main purpose is to attach pseudo-keys and alias resolution to things
    that can be inventoried (directories and YAML-files).
    """

    def __init__(self,
                 item: Mapping[_KT, _VT] | Path | None = None,
                 repo: onyo.lib.onyo.OnyoRepo | None = None,
                 **kwargs: _VT):
        super().__init__()
        self.repo: onyo.lib.onyo.OnyoRepo | None = repo
        self._path: Path | None = None
        self.data = CommentedMap()
        self.update(onyo.lib.pseudokeys.PSEUDO_KEYS)

        match item:
            case Item():
                self._path = item._path
                self.data = deepcopy(item.data)
            case Path():
                assert item.is_absolute()  # currently no support for relative. This is how all existing code should work ATM.
                self.update_from_path(item)
            case _ if item is not None:
                self.update(item)

        if kwargs:
            self.update(**kwargs)

    def __setitem__(self,
                    key,
                    value):
        key = resolve_alias(key)
        super().__setitem__(key, value)

    def __getitem__(self,
                    key):
        r"""Get the value of a ``key``.

        The initializer methods are referenced in the mapping
        :py:data:`onyo.lib.pseudokeys.PSEUDO_KEYS`. They are called on-demand,
        when a pseudo-key is first accessed.

        This allows to distinguish a meaningful ``None`` (<unset>) from a not
        yet evaluated pseudo-key.
        """

        key = resolve_alias(key)
        value = super().__getitem__(key)

        if key in onyo.lib.pseudokeys.PSEUDO_KEYS and \
                isinstance(value, onyo.lib.pseudokeys.PseudoKey):
            # Value still is the pseudo-key definition.
            # Actually load and set the response as the new value.
            new_value = value.implementation(self)
            self[key] = new_value
            return new_value

        return value

    def __delitem__(self,
                    key):
        return super().__delitem__(resolve_alias(key))

    def __contains__(self,
                     key):
        return super().__contains__(resolve_alias(key))

    def get(self,
            key,
            default=None):
        return super().get(resolve_alias(key), default=default)

    def update_from_path(self,
                         path: Path) -> None:
        """Update the internal dictionary with key/values from a YAML file.

        YAML comments are preserved on a best-effort basis. There is no
        straightforward way to merge YAML comments, and thus ones from ``path``
        may overwrite internal ones.

        Parameters
        ----------
        path
            Path of YAML file to update from.
        """

        from onyo.lib.utils import get_asset_content

        self._path = path

        if self['onyo.is.asset'] and self.repo:
            loader = self.repo.get_asset_content
        elif self['onyo.is.asset'] or self['onyo.is.template']:
            loader = get_asset_content
        else:
            return

        map_from_file = loader(path)
        self.update(map_from_file)
        if hasattr(map_from_file, 'copy_attributes'):
            # We got a (subclass of) ruamel.yaml.CommentBase.
            # Copy the attributes re comments, format, etc. for roundtrip.
            map_from_file.copy_attributes(self.data)  # pyre-ignore[16]

    def fill_created(self,
                     key: str | None = None):
        """Initializer for the ``'onyo.was.created'`` pseudo-keys.

        The entire ``'onyo.was.created'`` dict is initialized, regardless of
        which (if any) ``key`` is requested.

        Parameters
        ----------
        key
            Name of pseudo-key to get the value of.
        """

        # TODO: This is based on `git log --follow <path>`. The first appearance
        #       of 'new_assets'/'new_directories' should be the match. However,
        #       this is known to be problematic, both due to `git` and if the
        #       Python interface was used. A more robust solution will involve a
        #       more involved parsing of Inventory Operation records, and
        #       tracing history and moves, etc.

        if self['onyo.is.template']:
            # Templates aren't tracked by inventory operations (only in git).
            # Thus there are no operations records to be parsed.
            return None

        if self.repo and self['onyo.path.absolute']:
            for commit in self.repo.get_history(self['onyo.path.file']):  # pyre-ignore[16]
                if 'operations' in commit:
                    if (self['onyo.is.asset'] and commit['operations']['new_assets']) or \
                            (self['onyo.is.directory'] and commit['operations']['new_directories']):
                        self['onyo.was.created'] = commit.data
                        return commit[key] if key else None

            return None

    def fill_modified(self,
                      key: str | None = None):
        """Initializer for the ``'onyo.was.modified'`` pseudo-keys.

        The entire ``'onyo.was.modified'`` dict is initialized, regardless of
        which (if any) ``key`` is requested.

        Parameters
        ----------
        key
            Name of pseudo-key to get the value of.
        """

        # TODO: see `fill_created()` todo.

        if self['onyo.is.template']:
            # Templates aren't tracked by inventory operations (only in git).
            # Thus there are no operations records to be parsed.
            return None

        if self.repo and self['onyo.path.absolute']:
            for commit in self.repo.get_history(self['onyo.path.file']):  # pyre-ignore[16]
                if 'operations' in commit:
                    if (self['onyo.is.asset'] and
                        (commit['operations']['modify_assets'] or
                         commit['operations']['new_assets'])) or \
                       (self['onyo.is.directory'] and
                        (commit['operations']['new_directories'] or
                         commit['operations']['move_directories'] or
                         commit['operations']['rename_directories'])):
                        self['onyo.was.modified'] = commit.data
                        return commit[key] if key else None

        return None

    def get_path_absolute(self):
        """Initializer for the ``'onyo.path.absolute'`` pseudo-key."""

        if self.repo and self._path and self._path.name == self.repo.ASSET_DIR_FILE_NAME:
            return self._path.parent

        return self._path

    def get_path_relative(self):
        """Initializer for the ``'onyo.path.relative'`` pseudo-key."""

        if self.repo and self['onyo.path.absolute']:
            try:
                return self['onyo.path.absolute'].relative_to(self.repo.git.root)
            except ValueError:
                # return None (translates to '<unset>') if relative_to() fails b/c path is outside repo.
                pass

        return None

    def get_path_parent(self):
        """Initializer for the ``'onyo.path.parent'`` pseudo-key."""

        if self.repo and self['onyo.path.relative']:
            return self['onyo.path.relative'].parent

        return None

    def get_path_file(self):
        """Initializer for the ``'onyo.path.file'`` pseudo-key."""

        if self.repo and self['onyo.path.relative']:
            if not self['onyo.is.directory']:
                return self['onyo.path.relative']
            if self['onyo.is.asset'] or self['onyo.is.template']:
                return self['onyo.path.relative'] / onyo.lib.onyo.OnyoRepo.ASSET_DIR_FILE_NAME
            return self['onyo.path.relative'] / onyo.lib.onyo.OnyoRepo.ANCHOR_FILE_NAME

        return None

    def get_path_name(self):
        """Initializer for the ``'onyo.path.name'`` pseudo-key."""

        if self['onyo.path.absolute']:
            return self['onyo.path.absolute'].name

        return None

    def is_asset(self) -> bool | None:
        """Initializer for the ``'onyo.is.asset'`` pseudo-key."""

        if not self.repo or not self._path:
            return None

        return self.repo.is_asset_path(self._path)

    def is_directory(self) -> bool | None:
        """Initializer for the ``'onyo.is.directory'`` pseudo-key."""

        if not self.repo or not self._path:
            return None

        return self.repo.is_inventory_dir(self._path)

    def is_template(self) -> bool | None:
        """Initializer for the ``'onyo.is.template'`` pseudo-key."""

        if not self.repo or not self._path:
            return None

        return self.repo.git.root / self.repo.TEMPLATE_DIR in self._path.parents

    def is_empty(self) -> bool | None:
        """Initializer for the ``'onyo.is.empty'`` pseudo-key."""

        if self['onyo.is.directory'] and self.repo and self._path:
            # TODO: This likely can be faster when redoing/enhancing caching of repo paths.
            return not any(p.parent == self._path for p in self.repo.asset_paths)

        return None

# TODO/Notes for next PR(s):
# - Bug/Missing feature: pseudo-keys that are supposed to be settable by commands, are not yet
#   ensured to return bool/Path objects that the codebase acts upon when their values are coming in from
#   CLI or (template-)files, since everything is stringified now.
# - We need plain files/directories represented for --yaml
# - Templates can be (asset-) dirs  -> a dir is an item. If it has the dot yaml file, it's an asset dir
# - values in templates maybe to be evaluated matching expression or even plugin calls  #714
# - Path attribute caching at git/onyo layers (is_file, etc.):
#   We actually know that everything we get from
#   git ls-tree is in fact a file or symlink. And we can derive
#   dirs from that path list (.anchor). That may be a lot faster.
#   Implement cache dict at GitRepo level.
# - Probably/Maybe: Stop passing dicts and Path objects around. All things relevant at higher level are Items, right?
# - suck in DotNotationWrapper instead of deriving!? Probably not, because we have asset/template specs that should
#   behave with dot notation, but can't or even must not have pseudo-keys.
# - What about `__eq__` (see the horrible is_equal_dict helper)?
