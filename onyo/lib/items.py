from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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

    _KT = TypeVar("_KT")  # Key type.
    _VT = TypeVar("_VT")  # Value type.


def resolve_alias(key: Any) -> Any:
    """Return the target of a key alias."""
    try:
        return onyo.lib.pseudokeys.PSEUDOKEY_ALIASES[key]
    except KeyError:
        return key


class Item(DotNotationWrapper):
    """An Item an Inventory can potentially track.

    The main purpose of this class is to attach pseudo-keys
    and alias resolution to things that can be inventoried.
    That's directories and YAML-files.

    The initializer methods are referenced in the `PSEUDO_KEYS`
    mapping. They are called, when a pseudo-key is first
    accessed (see `self.__getitem__`). This allows to distinguish
    a meaningful `None` (<unset>) from a not yet evaluated
    pseudo-key.
    """

    def __init__(self,
                 item: Mapping[_KT, _VT] | Path | None = None,
                 repo: onyo.lib.onyo.OnyoRepo | None = None,
                 **kwargs: _VT):
        super().__init__()
        self.repo: onyo.lib.onyo.OnyoRepo | None = repo
        self.update(onyo.lib.pseudokeys.PSEUDO_KEYS)
        self._path = None

        if isinstance(item, Path):
            assert item.is_absolute()  # currently no support for relative. This is how all existing code should work ATM.
            self.update_from_path(item)
        elif item is not None:
            self.update(item)

        if kwargs:
            self.update(**kwargs)

    def __setitem__(self, key, value):
        key = resolve_alias(key)
        super().__setitem__(key, value)

    def __getitem__(self, key):
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

    def __delitem__(self, key):
        return super().__delitem__(resolve_alias(key))

    def __contains__(self, key):
        return super().__contains__(resolve_alias(key))

    def get(self, key, default=None):
        return super().get(resolve_alias(key), default=default)

    def update_from_path(self, path: Path):
        """Update internal dictionary from a YAML file."""
        # TODO: Potentially account for being pointed to
        #       a directory or an .onyoignore'd file.
        from onyo.lib.utils import get_asset_content
        self._path = path
        if self['onyo.is.asset']:
            loader = self.repo.get_asset_content if self.repo else get_asset_content
            self.update(loader(path))

    # TODO: git metadata:
    # def fill_created(self, what: str | None):
    #     # self.repo.git.xxx   (self.get('onyo.path.file'))
    #     # fill in all created keys
    #     # switch `what` -> return whatever part was requesting this
    #     pass#raise NotImplementedError
    #
    # def fill_modified(self, what: str | None):
    #     pass#raise NotImplementedError

    def get_path_absolute(self):
        """Initializer for the 'onyo.path.absolute' pseudo-key."""
        if self.repo and self._path and self._path.name == self.repo.ASSET_DIR_FILE_NAME:
            return self._path.parent
        return self._path

    def get_path_relative(self):
        """Initializer for the 'onyo.path.relative' pseudo-key."""
        if self.repo and self['onyo.path.absolute']:
            return self['onyo.path.absolute'].relative_to(self.repo.git.root)
        return None

    def get_path_parent(self):
        """Initializer for the 'onyo.path.parent' pseudo-key."""
        if self.repo and self['onyo.path.absolute']:
            return self['onyo.path.absolute'].parent.relative_to(self.repo.git.root)
        return None

    def get_path_file(self):
        """Initializer for the 'onyo.path.file' pseudo-key."""
        return self._path.relative_to(self.repo.git.root) if self.repo and self['onyo.is.asset'] else None

    def is_asset(self) -> bool | None:
        """Initializer for the 'onyo.is.asset' pseudo-key."""
        if not self.repo or not self._path:
            return None
        return self.repo.is_asset_path(self._path)

    def is_directory(self) -> bool | None:
        """Initializer for the 'onyo.is.directory' pseudo-key."""
        if not self.repo or not self._path:
            return None
        return self.repo.is_inventory_dir(self._path)

    def is_template(self) -> bool | None:
        """Initializer for the 'onyo.is.template' pseudo-key."""
        if not self.repo or not self._path:
            return None
        return self.repo.git.root / self.repo.TEMPLATE_DIR in self._path.parents

    def is_empty(self) -> bool | None:
        """Initializer for the 'onyo.is.empty' pseudo-key."""
        return None  # TODO: Unclear what exactly this needs to consider. Probably child items? Or just assets?

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
