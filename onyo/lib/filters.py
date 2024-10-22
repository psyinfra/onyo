from __future__ import annotations

import re
from dataclasses import dataclass, field

from onyo.lib.consts import UNSET_VALUE
from onyo.lib.exceptions import OnyoInvalidFilterError


@dataclass
class Filter:
    r"""This class translates a string expression to a match function
    suitable for the builtin `filter`.

    Intended for use with string patterns used with onyo's CLI.
    """
    _arg: str = field(repr=False)
    key: str = field(init=False)
    value: str = field(init=False)

    def __post_init__(self) -> None:
        r"""
        Set up a `key=value` conditional as a filter, to allow assets to be
        matched with the filter. Asset keys are then assessed on whether the
        given key matches the given value. This can be used along with the
        built-in filter to remove any non-matching assets.

        Example::

            repo = Repo()
            f = Filter('foo=bar')
            assets[:] = filter(f.match, repo.assets)
        """
        self.key, self.value = self._format(self._arg)

    @staticmethod
    def _format(arg: str) -> list[str]:
        r"""Split filters by the first occurrence of the `=` (equals) sign."""
        if not isinstance(arg, str) or '=' not in arg:
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')
        return arg.split('=', 1)

    @staticmethod
    def _re_match(text: str, r: str) -> bool:
        try:
            return True if re.compile(r).fullmatch(text) else False
        except re.error:
            return False

    def match(self, asset: dict) -> bool:
        r"""match self on a dictionary"""
        if self.value == UNSET_VALUE:
            # match if:
            #   - key is not present or
            #   - value is `None` or an empty string
            return self.key not in asset or asset[self.key] in [None, '']
        if self.key not in asset:
            # we can't match anything other than UNSET_VALUE, if key is not present
            return False

        asset_value = asset[self.key]

        # onyo type representation match
        string_types = {'<list>': list, '<dict>': dict}
        if self.value in string_types:
            return isinstance(asset_value, string_types[self.value])

        # match literal empty structure representations
        empty_structs = ['[]', '{}']
        if self.value in empty_structs:
            return str(asset_value) == self.value

        # equivalence and regex match
        return asset_value == self.value or self._re_match(str(asset_value), self.value)
