from __future__ import annotations

from collections import UserDict
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from ruamel.yaml import CommentedMap  # pyre-ignore[21]

from onyo.lib.consts import (
    ANCHOR_FILE_NAME,
    ASSET_DIR_FILE_NAME,
    RESERVED_KEYS,
)
from onyo.lib.pseudokeys import (
    PSEUDO_KEYS,
    PSEUDOKEY_ALIASES,
    PseudoKey,
)
from onyo.lib.utils import (
    dict_to_yaml,
    yaml_to_dict,
)


if TYPE_CHECKING:
    from typing import (
        Any,
        Generator,
        Mapping,
        TypeVar,
    )
    from onyo.lib.onyo import OnyoRepo

    _KT = TypeVar("_KT")  # Key type
    _VT = TypeVar("_VT")  # Value type


def resolve_alias(key: _KT,
                  alias_map: Mapping[str, str] | None = None) -> Any:
    r"""Return the target key of a key alias.

    Parameters
    ----------
    key
        Key name to resolve.
    alias_map
        Dictionary mapping aliases to key names.
    """

    alias_map = {} if alias_map is None else alias_map
    try:
        resolved_key = alias_map[key]
        # lookup again, in case it's an alias of an alias
        return resolve_alias(resolved_key, alias_map=alias_map)
    except KeyError:
        return key


class ItemSpec(UserDict):
    r"""Nested dictionaries of static instructions to create an ``Item``.

    Compared to a dictionary, the primary features are:

    * load YAML (e.g. ``ItemSpec(Path('file.yaml'))``
    * dump YAML (e.g. ``spec.yaml()``)
    * equality including YAML comments (e.g. ``ItemSpec() == ItemSpec()``)
    * dot notation (e.g. ``spec['nested.dict.key']``)
    * alias resolution

    In contrast to ``Item``, an ``ItemSpec`` is entirely static. It is not
    associated with a repository, and thus has no sanity checks nor pseudokey
    lookup capabilities. Alias resolution is possible, but the mapping must be
    provided manually.

    Multidimensional dictionaries are traversed using a dot as the delimiter.
    In other words, it provides a view of the flattened dictionary::

      > d = {'key': 'value', 'nested': {'key': 'another value'}}
      > spec = ItemSpec(d)
      > spec['nested.key']
      'another value'
      > list(spec.keys())
      ['key', 'nested.key']

    Iteration only considers the flattened view. Keys that contain a dictionary
    are not yielded when using ``.keys()``, ``.values()``, and ``.items()``.

    The underlying dictionary is available via the ``.data`` attribute when the
    standard Python behavior is needed.
    """

    def __init__(self,
                 __spec: Mapping[_KT, _VT] | str | None = None,
                 pristine_original: bool = True,
                 alias_map: Mapping[str, str] | None = None,
                 **kwargs: _VT) -> None:
        r"""Initialize an ItemSpec.

        Parameters
        ----------
        __spec
            Dictionary or YAML string to load.
        pristine_original
            Store ``__dict`` unaltered in the ``.data`` attribute.
            This behavior is the primary intended use for the wrapper: just a
            namespace wrapper for dicts.

            Set to ``False`` to interpret the incoming dict's keys for dot
            notation and set accordingly.
        alias_map
            Dictionary mapping aliases to key names.
        """

        self._alias_map: Mapping[str, str] = {} if alias_map is None else alias_map

        if isinstance(__spec, str):
            # TODO: unlike other input methods, this does /not/ do alias
            #       resolution on init
            __spec = yaml_to_dict(__spec)

        if pristine_original and __spec and isinstance(__spec, dict):
            # Maintain the original dict object (and class).
            # NOTE: Would modify wrapped dict w/ kwargs if both are given.
            #       deepcopy would prevent this, but contradicts the idea of wrapping.
            super().__init__()
            self.data = __spec
            self.update(**kwargs)
        else:
            # Resort to `UserDict` behavior.
            super().__init__(__spec, **kwargs)

    def __contains__(self,
                     key: _KT) -> bool:
        r"""Whether ``key`` is in self.

        Unlike iteration over keys, keys that contain a dictionary are
        matchable and return ``True``.
        """

        key = resolve_alias(key, alias_map=self._alias_map)

        try:
            self.__getitem__(key)
            return True
        except KeyError:
            return False

    def __delitem__(self,
                    key: _KT) -> None:
        r"""Remove a ``key`` from self."""

        key = resolve_alias(key, alias_map=self._alias_map)

        if isinstance(key, str):
            parts = key.split('.')
            effective_dict = self.data
            if len(parts) > 1:
                for lvl in range(len(parts) - 1):
                    try:
                        effective_dict = effective_dict[parts[lvl]]
                    except KeyError as e:
                        raise KeyError(f"'{'.'.join(parts[:lvl + 1])}'") from e
            del effective_dict[parts[-1]]
        else:
            super().__delitem__(key)

    def __getitem__(self,
                    key: _KT) -> Any:
        r"""Get the value of a key."""

        key = resolve_alias(key, alias_map=self._alias_map)

        if isinstance(key, str):
            parts = key.split('.')
            effective_dict = self.data
            if len(parts) > 1:
                for lvl in range(len(parts) - 1):
                    try:
                        effective_dict = effective_dict[parts[lvl]]
                    except KeyError as e:
                        raise KeyError(f"'{'.'.join(parts[:lvl + 1])}'") from e
                    except TypeError as e:
                        raise KeyError(f"'{'.'.join(parts[:lvl])}' is not a dictionary.") from e

            try:
                return effective_dict[parts[-1]]
            except KeyError as e:
                raise KeyError(f"'{key}'") from e
            except TypeError as e:
                raise KeyError(f"'{'.'.join(parts[:-1])}' is not a dictionary.") from e

        return super().__getitem__(key)

    def __iter__(self) -> Generator[str, None, None]:
        r"""Return the iterator.

        A by-product of dot notation is that all keys are strings, regardless of
        their original type in the underlying dictionary.

        Keys that contain a dictionary are not yielded.
        """

        return self._keys()

    def __len__(self) -> int:
        r"""Return the number of keys in the dot notation view.

        Keys that contain a dictionary are not counted.
        """

        return len(list(self._keys()))

    def __setitem__(self,
                    key: _KT,
                    value: _VT) -> None:
        r"""Set the value of a key.

        Keys that are strings are interpreted for dot notation, and intermediate
        dictionaries are created as needed.
        """

        key = resolve_alias(key, alias_map=self._alias_map)

        if isinstance(key, str):
            parts = key.split('.')
            effective_dict = self.data
            if len(parts) > 1:
                for lvl in range(len(parts) - 1):
                    try:
                        effective_dict = effective_dict[parts[lvl]]
                    except KeyError:
                        # nested dict doesn't exist yet
                        effective_dict[parts[lvl]] = dict()
                        effective_dict = effective_dict[parts[lvl]]

            effective_dict[parts[-1]] = value
        else:
            super().__setitem__(key, value)

    def _keys(self) -> Generator[str, None, None]:
        r"""Yield all keys recursively from nested dictionaries in dot notation.

        A by-product of dot notation is that all keys are strings, regardless of
        their original type in the underlying dictionary.

        Keys that contain a dictionary not yielded.
        """

        def recursive_keys(d: dict):
            for k in d.keys():
                if hasattr(d[k], "keys"):
                    yield from (k + "." + sk for sk in recursive_keys(d[k]))
                else:
                    # Cast as a string. One can't have a key 'some.1.more',
                    # where 1 remains an integer.
                    yield str(k)

        yield from recursive_keys(self.data)

    def equal_content(self,
                      other: ItemSpec | Item) -> bool:
        r"""Whether another ItemSpec/Item and self have the same content and comments.

        Pseudokeys are ignored entirely.

        Parameters
        ----------
        other
            Item to compare with self.
        """

        return self.yaml() == other.yaml()

    def get(self,  # pyre-ignore[14]
            key: _KT,
            default: Any = None) -> Any:
        r"""Return the value of ``key`` if it's in the dictionary, otherwise ``default``."""

        key = resolve_alias(key, alias_map=self._alias_map)

        return super().get(key, default=default)

    def update_from_path(self,
                         path: Path) -> None:
        r"""Update the internal dictionary with key/values from a YAML file.

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

        if self.repo and self.repo.is_asset_path(path):
            loader = self.repo.get_asset_content
        elif path.is_file():
            loader = get_asset_content
        else:
            return

        map_from_file = loader(path)
        self.update(map_from_file)
        if hasattr(map_from_file, 'copy_attributes'):
            # We got a (subclass of) ruamel.yaml.CommentBase.
            # Copy the attributes re comments, format, etc. for roundtrip.
            map_from_file.copy_attributes(self.data)  # pyre-ignore[16]

    def yaml(self,
             exclude: list | None = None) -> str:
        r"""Get the stringified YAML including content and comments.

        Parameters
        ----------
        exclude
            Keys to exclude from the output. By default, all
            :py:data:`onyo.lib.consts.RESERVED_KEYS` (e.g. pseudokeys) are
            excluded.
        """

        exclude = RESERVED_KEYS if exclude is None else exclude

        # deepcopy to keep comments
        content = deepcopy(self)
        for key in exclude:
            if key in content:
                del content[key]

        return dict_to_yaml(content.data)


class Item(ItemSpec):
    r"""An item that an :py:class:`onyo.lib.inventory.Inventory` can potentially track.

    In contrast to an ``ItemSpec``, an ``Item`` is associated with a repository.
    Thus, it gains the ability to lookup/generate pseudokey values and the
    automatic resolution of user-defined key aliases.

    On initialization, sanity checks are performed on the provided
    pseudokey-related values (e.g. all ``'onyo.path'`` are consistent, generate
    the asset name from keys, etc). However, once instantiated, ``Item`` allows
    changes to be made and makes no assurances about the consistency of the
    information stored in it. For example, modifying ``onyo.is.directory`` or a
    key used in the asset name will not automatically update the value of
    ``onyo.path.file``.

    It is the responsibility of those modifying values to clear caches and
    ensure consistency.

    It is safest to use the operations available in :py:class:`onyo.lib.inventory.Inventory`
    to modify Items.
    """

    def __init__(self,
                 item: Mapping[_KT, _VT] | Path | None = None,
                 repo: OnyoRepo | None = None,
                 **kwargs: _VT) -> None:
        r"""Initialize an Item."""

        super().__init__()
        self.repo: OnyoRepo | None = repo
        self._path: Path | None = None
        self._alias_map: Mapping[str, str] = PSEUDOKEY_ALIASES
        self.data = CommentedMap()
        self.update(PSEUDO_KEYS)

        match item:
            case ItemSpec():
                self._path = getattr(item, '_path', None)
                self.data = deepcopy(item.data)
            case Item():
                self._path = item._path
                self.data = deepcopy(item.data)
            case Path():
                assert item.is_absolute()  # currently no support for relative. This is how all existing code should work ATM.
                self._path = item
                self.update_from_path(item)
            case _ if item is not None:
                self.update(item)

        if kwargs:
            self.update(**kwargs)

    def __eq__(self,
               other: Any) -> bool:
        r"""Whether another Item and self have the same content, comments, and paths.

        Pseudokeys are ignored with the exception of:

        - `'onyo.is.asset'`
        - `'onyo.is.directory'`
        - `'onyo.path.absolute'`
        - `'onyo.path.file'`
        - `'onyo.path.name'`
        - `'onyo.path.relative'`
        """

        if not isinstance(other, Item):
            return False

        # NOTE: 'onyo.path.file' is checked first because it actually covers all
        #       other tests. The other keys are kept to be self-documenting and
        #       to protect against future implementation changes causing bugs.
        pseudo_keys_to_check = [
            'onyo.path.file',
            'onyo.is.asset',
            'onyo.is.directory',
            'onyo.path.absolute',
            'onyo.path.name',
            'onyo.path.relative',
        ]
        for k in pseudo_keys_to_check:
            if self.get(k, None) != other.get(k, None):
                return False

        return self.equal_content(other)

    def __getitem__(self,
                    key: _KT) -> Any:
        r"""Get the value of a ``key``.

        The initializer methods are referenced in the mapping
        :py:data:`onyo.lib.pseudokeys.PSEUDO_KEYS`. They are called on-demand,
        when a pseudo-key is first accessed.

        This allows to distinguish a meaningful ``None`` (<unset>) from a not
        yet evaluated pseudo-key.
        """

        value = super().__getitem__(key)

        if key in PSEUDO_KEYS and isinstance(value, PseudoKey):
            # Value still is the pseudo-key definition.
            # Actually load and set the response as the new value.
            new_value = value.implementation(self)
            self[key] = new_value
            return new_value

        return value

    def _fill_created(self,
                      key: str | None = None) -> str | None:
        r"""Initializer for the ``'onyo.was.created'`` pseudo-keys.

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

    def _fill_modified(self,
                       key: str | None = None) -> str | None:
        r"""Initializer for the ``'onyo.was.modified'`` pseudo-keys.

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

    def _get_path_absolute(self) -> Path | None:
        r"""Initializer for the ``'onyo.path.absolute'`` pseudo-key."""

        if self.repo and self._path and self._path.name == ASSET_DIR_FILE_NAME:
            return self._path.parent

        return self._path

    def _get_path_file(self) -> Path | None:
        r"""Initializer for the ``'onyo.path.file'`` pseudo-key."""

        if self.repo and self['onyo.path.relative']:
            if self['onyo.is.directory']:
                if self['onyo.is.asset']:
                    return self['onyo.path.relative'] / ASSET_DIR_FILE_NAME

                return self['onyo.path.relative'] / ANCHOR_FILE_NAME

            return self['onyo.path.relative']

        return None

    def _get_path_name(self) -> str | None:
        r"""Initializer for the ``'onyo.path.name'`` pseudo-key."""

        if self['onyo.path.absolute']:
            return self['onyo.path.absolute'].name

        return None

    def _get_path_parent(self) -> Path | None:
        r"""Initializer for the ``'onyo.path.parent'`` pseudo-key."""

        if self.repo and self['onyo.path.relative']:
            return self['onyo.path.relative'].parent

        return None

    def _get_path_relative(self) -> Path | None:
        r"""Initializer for the ``'onyo.path.relative'`` pseudo-key."""

        if self.repo and self['onyo.path.absolute']:
            try:
                return self['onyo.path.absolute'].relative_to(self.repo.git.root)  # pyre-ignore[16]
            except ValueError:
                # return None (translates to '<unset>') if relative_to() fails b/c path is outside repo.
                pass

        return None

    def _is_asset(self) -> bool | None:
        r"""Initializer for the ``'onyo.is.asset'`` pseudo-key."""

        if not self.repo or not self._path:
            return None

        # True, if the item is either an existing asset in the inventory or
        # it's representing "instructions" for creating one.
        # The latter implies it has non-pseudo-keys, or it is specifying "onyo.is.asset"
        # itself in which case this implementation here will be overruled anyway.
        return self.repo.is_asset_path(self._path) or \
            any(k not in PSEUDO_KEYS for k in self.keys())

    def _is_directory(self) -> bool | None:
        r"""Initializer for the ``'onyo.is.directory'`` pseudo-key."""

        if not self.repo or not self._path:
            return None

        # True, if it's either an existing inventory dir or a template dir.
        # TODO: `is_dir()` should be looking up git-committed dirs instead. -> Property at OnyoRepo
        return self.repo.is_inventory_dir(self._path) or (self._path.is_dir() and self["onyo.is.template"])  # pyre-ignore[16]

    def _is_empty(self) -> bool | None:
        r"""Initializer for the ``'onyo.is.empty'`` pseudo-key."""

        if self['onyo.is.directory'] and self.repo and self._path:
            # TODO: This likely can be faster when redoing/enhancing caching of repo paths.
            return not any(p.parent == self._path for p in self.repo.asset_paths)

        return None

    def _is_template(self) -> bool | None:
        r"""Initializer for the ``'onyo.is.template'`` pseudo-key."""

        if not self.repo or not self._path:
            return None

        return self._path == self.repo.template_dir or self.repo.template_dir in self._path.parents   # pyre-ignore[16]

# TODO/Notes for next PR(s):
# - Bug/Missing feature: pseudo-keys that are supposed to be settable by commands, are not yet
#   ensured to return bool/Path objects that the codebase acts upon when their values are coming in from
#   CLI or (template-)files, since everything is stringified now.
# - We need plain files/directories represented for --yaml
# - values in templates maybe to be evaluated matching expression or even plugin calls  #714
# - Path attribute caching at git/onyo layers (is_file, etc.):
#   We actually know that everything we get from
#   git ls-tree is in fact a file or symlink. And we can derive
#   dirs from that path list (.anchor). That may be a lot faster.
#   Implement cache dict at GitRepo level.
