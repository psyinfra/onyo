from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from typing import (
        Callable,
        Dict,
    )
    from onyo.lib.items import Item


@dataclass()
class PseudoKey:
    r""""Define a pseudo-key implementation."""

    description: str
    r"""Description of the pseudo-key's value."""

    implementation: Callable
    r"""Callable to populate the pseudo-key's value when it is undefined.

    The Callable is expected to accept a single parameter of type
    :py:class:`onyo.lib.items.Item`.
    """

    def __eq__(self,
               other) -> bool:
        r"""Whether another ``PseudoKey`` matches self."""

        if not isinstance(other, PseudoKey):
            return False

        # TODO: This isn't clean yet, since it relies on `implementation` being a `partial`:
        return self.description == other.description and self.implementation.func == other.implementation.func  # pyre-ignore[16]


def delegate(self: Item,
             attribute: str,
             *args,
             **kwargs):
    r"""Call function ``attribute`` and pass all args.

    To avoid circular imports between this file and :py:data`onyo.lib.inventory.OPERATIONS_MAPPING`.
    """

    return self.__getattribute__(attribute)(*args, **kwargs)


PSEUDO_KEYS: Dict[str, PseudoKey] = {
    'onyo.path.absolute': PseudoKey(
        description="Absolute path of the item.",
        implementation=partial(delegate, attribute='get_path_absolute')
    ),
    'onyo.path.relative': PseudoKey(
        description="Path of the item relative to the repository root.",
        implementation=partial(delegate, attribute='get_path_relative')
    ),
    'onyo.path.parent': PseudoKey(
        description="Path of the directory the item is in, relative to the repository root.",
        implementation=partial(delegate, attribute='get_path_parent')
    ),
    'onyo.path.file': PseudoKey(
        description="Path to the file containing an asset's YAML."
                    "Different from 'onyo.path.relative' in case of an asset directory.",
        implementation=partial(delegate, attribute='get_path_file')
    ),
    'onyo.path.name': PseudoKey(
        description="Basename of the item's path.",
        implementation=partial(delegate, attribute='get_path_name')
    ),
    'onyo.is.asset': PseudoKey(
        description="Is the item an asset.",
        implementation=partial(delegate, attribute='is_asset')
    ),
    'onyo.is.directory': PseudoKey(
        description="Is the item a directory.",
        implementation=partial(delegate, attribute='is_directory')
    ),
    'onyo.is.template': PseudoKey(
        description="Is the item a template.",
        implementation=partial(delegate, attribute='is_template')
    ),
    'onyo.is.empty': PseudoKey(
        description="Is the directory empty. <unset> if the item is not a directory.",
        implementation=partial(delegate, attribute='is_empty')
    ),
    'onyo.was.modified.hexsha': PseudoKey(
        description="SHA of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', key='hexsha')
    ),
    'onyo.was.modified.time': PseudoKey(
        description="Time of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', key='time')
    ),
    'onyo.was.modified.author.name': PseudoKey(
        description="Name of the author of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', key='author.time')
    ),
    'onyo.was.modified.author.email': PseudoKey(
        description="Email of the author of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', key='author.email')
    ),
    'onyo.was.modified.committer.name': PseudoKey(
        description="Name of the committer of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', key='committer.name')
    ),
    'onyo.was.modified.committer.email': PseudoKey(
        description="Email of the committer of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', key='committer.email')
    ),
    'onyo.was.created.hexsha': PseudoKey(
        description="SHA of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', key='hexsha')
    ),
    'onyo.was.created.time': PseudoKey(
        description="Time of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', key='time')
    ),
    'onyo.was.created.author.name': PseudoKey(
        description="Name of the author of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', key='author.time')
    ),
    'onyo.was.created.author.email': PseudoKey(
        description="Email of the author of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', key='author.email')
    ),
    'onyo.was.created.committer.name': PseudoKey(
        description="Name of the committer of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', key='committer.name')
    ),
    'onyo.was.created.committer.email': PseudoKey(
        description="Email of the committer of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', key='committer.email')
    ),
}
r"""Addressable keys that are not part of the on-disk asset YAML.

For example, git commit metadata and path information.

All ``PSEUDO_KEYS`` are reserved.

See Also
--------
RESERVED_KEYS
"""

# Hardcode aliases for now:
# Introduction of proper aliases requires config cache first.
PSEUDOKEY_ALIASES: Dict[str, str] = {
    'path': 'onyo.path.relative',
    'directory': 'onyo.path.parent',
}
r"""Aliases that map a key name to another."""
