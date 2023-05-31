from __future__ import annotations
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from onyo.lib.exceptions import OnyoInvalidFilterError


log: logging.Logger = logging.getLogger('onyo.filters')


# TODO: Move this to a place specifically meant for defaults, along with
#  other defaults like <list>, <dict>, and potentially <none> or <null>
UNSET_VALUE = '<unset>'


def asset_name_to_keys(path: Path, pseudo_keys: list[str]) -> dict[str, str]:
    """Convert an asset name to pseudo key values"""
    return dict(zip(
        pseudo_keys,
        re.findall(r'(^[^._]+?)_([^._]+?)_([^._]+?)\.(.+)', path.name)[0]))


@dataclass
class Filter:
    _arg: str = field(repr=False)
    key: str = field(init=False)
    value: str = field(init=False)
    _pseudo_keys: list[str] = field(init=False, default_factory=list)

    def __post_init__(self):
        """
        Set up a `key=value` conditional as a filter, to allow assets to be
        matched with the filter. Asset keys are then assessed on whether the
        given key matches the given value. This can be used along with the
        built-in filter to remove any non-matching assets.

        Example::

            repo = Repo()
            f = Filter('foo=bar')
            assets[:] = filter(f.match, repo.assets)
        """
        from onyo.lib.assets import PSEUDO_KEYS  # delayed import; would be circular otherwise
        self._pseudo_keys = PSEUDO_KEYS
        self.key, self.value = self._format(self._arg)

    @staticmethod
    def _format(arg: str) -> list[str]:
        """Split filters by the first occurrence of the `=` (equals) sign."""
        if not isinstance(arg, str) or '=' not in arg:
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')
        return arg.split('=', 1)

    @property
    def is_pseudo(self) -> bool:
        return True if self.key in self._pseudo_keys else False

    @staticmethod
    def _re_match(text: str, r: str) -> bool:
        try:
            return True if re.compile(r).fullmatch(text) else False
        except re.error:
            return False

    def match(self, asset: Path) -> bool:
        """match self on asset contents which must be loaded first"""
        unset = UNSET_VALUE
        string_types = {'<list>': list, '<dict>': dict}

        # filters checking pseudo keys only need to access asset Path
        if self.is_pseudo:
            data = asset_name_to_keys(asset, self._pseudo_keys)
            re_match = self._re_match(str(data[self.key]), self.value)
            if re_match or self.value == data[self.key]:
                return True
            return False

        from onyo.lib.assets import read_asset
        data = read_asset(asset)

        # Check if filter is <unset> and there is no data
        if not data and self.value == unset:
            return True
        elif self.key not in data.keys() and self.value == unset:
            return True
        elif self.key in data.keys() and self.value == unset and (
                data[self.key] is None or data[self.key] == ''):
            return True
        elif self.key not in data.keys() or self.value == unset:
            return False

        # equivalence and regex match
        re_match = self._re_match(str(data[self.key]), self.value)
        if re_match or data[self.key] == self.value:
            return True

        # onyo type representation match
        if self.value in string_types:
            return True if isinstance(
                data[self.key], string_types[self.value]) else False

        return False
