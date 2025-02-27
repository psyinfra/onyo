from __future__ import annotations

import re
from dataclasses import (
    dataclass,
    field,
)
from typing import TYPE_CHECKING

from onyo.lib.consts import (
    SORT_DESCENDING,
    TAG_MAP_TYPES,
    TAG_EMPTY,
    TAG_UNSET,
    TAG_MAP_VALUES,
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
    operator: str = field(init=False)

    def __post_init__(self) -> None:
        r"""Set up a ``key=value`` conditional as a filter.

        ``value`` must be a valid Python regular expression.
        """

        self.key, self.operator, self.value = self._format(self._arg)

    @staticmethod
    def _format(arg: str) -> Tuple[str, str, str]:
        r"""Split filters on the first occurrence of an operator.

        Valid operators are ``=``, ``!=``, ``>``, ``>=``, ``<``, and ``<=``.

        Parameters
        ----------
        arg
            Raw string to split

        Raises
        ------
        OnyoInvalidFilterError
            No valid operator was found.
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
                operator = "<="
            case ">=":
                operator = ">="
            case "!=":
                operator = "!="
            case _:
                operator = arg[index]

        if index in (0, len(arg) - len(operator)):
            raise OnyoInvalidFilterError(
                'Filters must be formatted as `key=value`')

        key, value = arg.split(operator, 1)

        return key, operator, value

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

    def _tags_or_types_match(self,
                             item: Item) -> bool | None:
        r"""Whether the tags or types of ``self.value`` equals ``Item[self.key]``.

        Parameters
        ----------
        item
            Item to compare against.
        """

        if self.value == TAG_UNSET:
            # match if the key is not present
            return self.key not in item

        if self.key not in item:
            # we can't match anything other than TAG_UNSET, if key is not present
            raise ValueError

        item_value = item[self.key]

        # onyo type representation match (<list>, <dict>, etc)
        if self.value in TAG_MAP_TYPES:
            return isinstance(item_value, TAG_MAP_TYPES[self.value])

        # onyo value representation match (<false>, <null>, <true>, etc)
        if self.value in TAG_MAP_VALUES:
            return item_value is TAG_MAP_VALUES[self.value]

        # <empty> is special
        if self.value == TAG_EMPTY:
            return any(item_value == x for x in [None, '', [], {}])

        # literal empty structure representations
        match self.value:
            case '[]' | '{}':
                return str(item_value) == self.value
            case '""' | "''":
                return str(item_value) == ''

        return None

    def _match_equal(self,
                     item: Item) -> bool:  # pyre-ignore[7]
        r"""Whether ``self.value`` equals ``Item[self.key]``.

        Parameters
        ----------
        item
            Item to compare against.
        """

        result = self._tags_or_types_match(item)

        match result:
            case True|False:
                return result
            case None:
                return item[self.key] == self.value

    def _match_equal_with_re(self,
                             item: Item) -> bool:  # pyre-ignore[7]
        r"""Whether ``self.value`` equals ``Item[self.key]``.

        Regex is supported.

        Parameters
        ----------
        item
            Item to compare against.
        """

        result = self._tags_or_types_match(item)

        match result:
            case True|False:
                return result
            case None:
                # equivalence and regex match
                item_value = item[self.key]
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

        return not self._match_equal_with_re(item)

    def _match_greater_than(self,
                            item: Item) -> bool:
        r"""Whether ``self.value`` is > ``Item[self.key]``.

        A natural sort is used (i.e. '300' > '5').

        Parameters
        ----------
        item
            Item to compare against.
        """

        if self.value in [*TAG_MAP_TYPES, *TAG_MAP_VALUES, TAG_EMPTY, TAG_UNSET]:
            # type comparisons are not possible
            raise ValueError

        if self.key not in item:
            # comparison with nothing is not possible
            raise ValueError

        item_value = item[self.key]

        # literal empty structures ([], {})
        empty_structs = {'[]': list, '{}': dict, '""': str, "''": str}
        if self.value in empty_structs:
            if isinstance(item_value, empty_structs[self.value]):
                # an non-empty dict/list/string is indeed greater than an empty one
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

        if self.value in [*TAG_MAP_TYPES, *TAG_MAP_VALUES, TAG_EMPTY, TAG_UNSET]:
            # type comparisons are not possible
            raise ValueError

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

        if self.value in [*TAG_MAP_TYPES, *TAG_MAP_VALUES, TAG_EMPTY, TAG_UNSET]:
            # type comparisons are not possible
            raise ValueError

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
            No valid operator was found.
        """

        try:
            match self.operator:
                case "=":
                    return self._match_equal_with_re(item)
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
