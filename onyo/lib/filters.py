from __future__ import annotations

import re
from dataclasses import (
    dataclass,
    field,
)
from typing import TYPE_CHECKING

from onyo.lib.consts import (
    SORT_DESCENDING,
    TYPE_SYMBOL_MAPPING,
    UNSET_VALUE,
)
from onyo.lib.exceptions import OnyoInvalidFilterError
from onyo.lib.items import Item
from onyo.lib.command_utils import natural_sort

if TYPE_CHECKING:
    from typing import Tuple


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
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')

        match arg[index:index + 2]:
            case "<=":
                operand = "<="
            case ">=":
                operand = ">="
            case "!=":
                operand = "!="
            case _:
                operand = arg[index]

        if index in (0, len(arg) - len(operand)):
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

    def _match_equal(self,
                     item: Item) -> bool:
        r"""Whether ``self.value`` equals ``Item[self.key]``.

        Regex is supported.

        Parameters
        ----------
        item
            Item to compare against.
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

    def _match_not_equal(self,
                     item: Item) -> bool:
        r"""Whether ``self.value`` does not equal ``Item[self.key]``.

        Regex is supported.

        Parameters
        ----------
        item
            Item to compare against.
        """

        return not self._match_equal(item)

    def _match_greater_than(self,
                            item: Item) -> bool:
        r"""Whether ``self.value`` is > ``Item[self.key]``.

        A natural sort is used (i.e. '300' > '5').

        Parameters
        ----------
        item
            Item to compare against.
        """

        if self.value in TYPE_SYMBOL_MAPPING or self.value == UNSET_VALUE:
            # type comparisons are not possible
            raise ValueError

        if self.key not in item:
            # comparison with nothing is not possible
            raise ValueError

        item_value = item[self.key]

        # literal empty structures ([], {})
        empty_structs = {'[]': list, '{}': dict}
        if self.value in empty_structs:
            if isinstance(item_value, empty_structs[self.value]):
                # an non-empty dict/list is indeed greater than an empty one
                return bool(item_value)
            else:
                # comparison is not possible
                raise ValueError

        # ``item`` is intentionally put second in the list, so that it will stay
        # in place when the compared key values match, and only move up when
        # it's indeed greater.
        item_list = [
            Item({self.key: self.value}),
            item,
        ]
        keys = {
            self.key: SORT_DESCENDING,
        }
        sorted_item_list = natural_sort(item_list, keys=keys)  # pyre-ignore[6]

        return sorted_item_list[0] == item

    def _match_greater_than_or_equal(self,
                                     item: Item) -> bool:
        r"""Whether ``self.value`` is >= ``Item[self.key]``.

        A natural sort is used (i.e. '300' > '5').

        Parameters
        ----------
        item
            Item to compare against.
        """

        if self._match_equal(item):
            return True

        return self._match_greater_than(item)

    def _match_less_than(self,
                         item: Item) -> bool:
        r"""Whether ``self.value`` is < ``Item[self.key]``.

        A natural sort is used (i.e. '5' < '300').

        Parameters
        ----------
        item
            Item to compare against.
        """

        return not self._match_greater_than_or_equal(item)

    def _match_less_than_or_equal(self,
                                  item: Item) -> bool:
        r"""Whether ``self.value`` is <= ``Item[self.key]``.

        A natural sort is used (i.e. '5' < '300').

        Parameters
        ----------
        item
            Item to compare against.
        """

        if self._match_equal(item):
            return True

        return not self._match_greater_than(item)

    def match(self,
              item: Item) -> bool:
        r"""Does ``item`` match this ``Filter``.

        Parameters
        ----------
        item
            Item to match against.

        Raises
        ------
        OnyoInvalidFilterError
            No valid operand was found.
        """

        try:
            match self.operand:
                case "=":
                    return self._match_equal(item)
                case "!=":
                    return self._match_not_equal(item)
                case ">":
                    return self._match_greater_than(item)
                case ">=":
                    return self._match_greater_than_or_equal(item)
                case "<":
                    return self._match_less_than(item)
                case "<=":
                    return self._match_less_than_or_equal(item)
                case _:
                    raise OnyoInvalidFilterError
        except ValueError:
            # when the question makes no sense, return False
            return False
