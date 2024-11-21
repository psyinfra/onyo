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
}
r"""Pseudo-Keys are key names that are addressable but not written to disk in asset YAML.

All ``PSEUDO_KEYS`` are reserved.

See Also
--------
RESERVED_KEYS
"""

# 'onyo.git.created.time': PseudoKey(description="Datetime the inventory item was created.",
#                                    implementation=partial(delegate,
#                                                           attribute='fill_created',
#                                                           what='time')
#                                    # or onyo.git.created.time for an "return self.get(what)" in implementation?
#                                    ),
# 'onyo.git.created.commit': PseudoKey(description="Commit SHA of the commit the object was created in",
#                                      implementation=partial(delegate,
#                                                             attribute='fill_created',
#                                                             what='SHA')
#                                      ),

# 'onyo.git.created.committer.name': None,
                   # 'onyo.git.created.committer.email': None,
                   # 'onyo.git.created.author.name': None,
                   # 'onyo.git.created.author.email': None,
                   # 'onyo.git.modified.time': None,
                   # 'onyo.git.modified.commit': None,
                   # 'onyo.git.modified.committer.name': None,
                   # 'onyo.git.modified.committer.email': None,
                   # 'onyo.git.modified.author.name': None,
                   # 'onyo.git.modified.author.email': None,
                   #
                   #          },
                   #  }
                   # }

# Hardcode aliases for now:
# Introduction of proper aliases requires config cache first.
PSEUDOKEY_ALIASES: Dict[str, str] = {
    'path': 'onyo.path.relative',
    'directory': 'onyo.path.parent',
}
