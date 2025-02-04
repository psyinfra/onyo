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
    """"Defines a pseudo-key implementation."""
    description: str
    """description of what that pseudo-key is delivering"""
    implementation: Callable
    """Called by an `Item` when a pseudo-keys value is still undefined.

    This Callable is expected to have a single parameter of type `Item`.
    """

    def __eq__(self, other):
        if not isinstance(other, PseudoKey):
            return False

        # TODO: This isn't clean yet, since it relies on `implementation` being a `partial`:
        return self.description == other.description and self.implementation.func == other.implementation.func


def delegate(self: Item, attribute: str, *args, **kwargs):
    # This is to avoid circular imports ATM.
    return self.__getattribute__(attribute)(*args, **kwargs)


PSEUDO_KEYS: Dict[str, PseudoKey] = {
    'onyo.path.absolute': PseudoKey(description="Absolute path of the item.",
                                    implementation=partial(delegate, attribute='get_path_absolute')
                                    ),
    'onyo.path.relative': PseudoKey(description="Path of the item relative to the repository root.",
                                    implementation=partial(delegate, attribute='get_path_relative')
                                    ),
    'onyo.path.parent': PseudoKey(description="Path of the directory the item is in, relative to the repository root.",
                                  implementation=partial(delegate, attribute='get_path_parent')
                                  ),
    'onyo.path.file': PseudoKey(description="Path to the file containing an asset's YAML."
                                            "Different from 'onyo.path.relative' in case of an asset directory.",
                                implementation=partial(delegate, attribute='get_path_file')
                                ),
    'onyo.is.asset': PseudoKey(description="Is the item an asset.",
                               implementation=partial(delegate, attribute='is_asset')
                               ),
    'onyo.is.directory': PseudoKey(description="Is the item a directory.",
                                   implementation=partial(delegate, attribute='is_directory')
                                   ),
    'onyo.is.template': PseudoKey(description="Is the item a template.",
                                  implementation=partial(delegate, attribute='is_template')
                                  ),
    'onyo.is.empty': PseudoKey(description="Is the directory empty. <unset> if the item is not a directory.",
                               implementation=partial(delegate, attribute='is_empty')
                               ),
    'onyo.was.modified.hexsha': PseudoKey(description="SHA of the most recent commit that modified the item.",
                                          implementation=partial(delegate, attribute='fill_modified', what='hexsha')
                                          ),
    'onyo.was.modified.time': PseudoKey(description="Time of the most recent commit that modified the item.",
                                        implementation=partial(delegate, attribute='fill_modified', what='time')),
    'onyo.was.modified.author.name': PseudoKey(
        description="Name of the author of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', what='author.time')
    ),
    'onyo.was.modified.author.email': PseudoKey(
        description="Email of the author of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', what='author.email')
    ),
    'onyo.was.modified.committer.name': PseudoKey(
        description="Name of the committer of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', what='committer.name')
    ),
    'onyo.was.modified.committer.email': PseudoKey(
        description="Email of the committer of the most recent commit that modified the item.",
        implementation=partial(delegate, attribute='fill_modified', what='committer.email')
    ),
    'onyo.was.created.hexsha': PseudoKey(description="SHA of the commit that created the item.",
                                         implementation=partial(delegate, attribute='fill_created', what='hexsha')
                                         ),
    'onyo.was.created.time': PseudoKey(description="Time of the commit that created the item.",
                                       implementation=partial(delegate, attribute='fill_created', what='time')),
    'onyo.was.created.author.name': PseudoKey(
        description="Name of the author of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', what='author.time')
    ),
    'onyo.was.created.author.email': PseudoKey(
        description="Email of the author of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', what='author.email')
    ),
    'onyo.was.created.committer.name': PseudoKey(
        description="Name of the committer of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', what='committer.name')
    ),
    'onyo.was.created.committer.email': PseudoKey(
        description="Email of the committer of the commit that created the item.",
        implementation=partial(delegate, attribute='fill_created', what='committer.email')
    ),
}
r"""Pseudo-Keys are key names that are addressable but not written to disk in asset YAML.

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
