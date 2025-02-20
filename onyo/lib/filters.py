from __future__ import annotations

import re
from dataclasses import (
    dataclass,
    field,
)
from typing import TYPE_CHECKING

from onyo.lib.consts import (
    TYPE_SYMBOL_MAPPING,
    UNSET_VALUE,
)
from onyo.lib.exceptions import OnyoInvalidFilterError

if TYPE_CHECKING:
    from typing import Tuple
    from onyo.lib.items import Item


@dataclass
class Filter:
    r"""Translate a string regular expression to a match function.

    Intended for use with string patterns passed from Onyo's CLI.

    This can be used along with builtin :py:func:`filter` to remove non-matching
    items. For example::

        repo = Repo()
        f = Filter('foo=bar')
        assets[:] = filter(f.match, repo.assets)
    """

    _arg: str = field(repr=False)
    key: str = field(init=False)
    value: str = field(init=False)
    operand: str = field(init=False)

    def __post_init__(self) -> None:
        r"""Set up a ``key=value`` conditional as a filter.

        ``value`` must be a valid Python regular expression.
        """

        self.key, self.operand, self.value = self._format(self._arg)

    @staticmethod
    def _format(arg: str) -> Tuple[str, str, str]:
        r"""Split filters on the first occurrence of an operand.

        Valid operands are ``=``, ``!=``, ``>``, ``>=``, ``<``, and ``<=``.

        Parameters
        ----------
        arg
            Raw string to split

        Raises
        ------
        OnyoInvalidFilterError
            No valid operand was found.
        """

        index = None
        for c in ['=', '!=', '>', '<']:
            if c in arg:
                idx = arg.index(c)
                index = idx if index is None or idx < index else index

        if index is None:
            # TODO: fix error message
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')

        match arg[index:index + 2]:  # TODO: overflow bug
            case "<=":
                operand = "<="
            case ">=":
                operand = ">="
            case "!=":
                operand = "!="
            case _:
                operand = arg[index]

        if index in (0, len(arg) - len(operand)):
            # TODO: fix error message
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')

        key, value = arg.split(operand, 1)

        return key, operand, value

    @staticmethod
    def _re_match(text: str,
                  r: str) -> bool:
        r"""Does a whole string fully match a regular expression pattern.

        Parameters
        ----------
        text
            String to match
        r
            Regular expression Pattern
        """

        try:
            return True if re.compile(r).fullmatch(text) else False
        except re.error:
            return False

    def match(self,
              item: Item) -> bool:
        r"""Does ``item`` match this ``Filter``.

        Parameters
        ----------
        item
            Item to match against.
        """

        if self.value == UNSET_VALUE:
            # match if:
            #   - key is not present or
            #   - value is `None` or an empty string
            return self.key not in item or item[self.key] in [None, '']

        if self.key not in item:
            # we can't match anything other than UNSET_VALUE, if key is not present
            return False

        item_value = item[self.key]

        # onyo type representation match (<list>, <dict>, etc)
        if self.value in TYPE_SYMBOL_MAPPING:
            return isinstance(item_value, TYPE_SYMBOL_MAPPING[self.value])

        # match literal empty structure representations
        empty_structs = ['[]', '{}']
        if self.value in empty_structs:
            return str(item_value) == self.value

        # equivalence and regex match
        return item_value == self.value or self._re_match(str(item_value), self.value)
