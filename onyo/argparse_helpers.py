from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        Literal,
        Sequence,
    )


class StoreMultipleKeyValuePairs(argparse.Action):
    r"""Store a list of dictionaries of key-value pairs."""

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 key_values: list[str],
                 option_string: str | None = None) -> None:
        r"""Turn a list of 'KEY=VALUE' pairs into a list of dictionaries.

        Each key can be defined either 1 or N times (where N is the number of
        dictionaries to be created).

        A key that is declared once will apply to all dictionaries.

        All keys appearing N times must appear the same number of times. If not,
        a message will print to standard error and the program will exit with
        status code 2.

        Parameters
        ----------
        parser
            ArgumentParser object that contains this action.
        namespace
            Namespace object returned by :py:meth:`argparse.ArgumentParser.parse_args`.
        key_values
            List of strings containing key-value pairs.
        option_string
            Option string used to invoke this action.
        """

        for kv in key_values:
            if "=" not in kv:
                parser.error(f"Invalid argument '{kv}'. Expected key-value pairs '<key>=<value>'.")

        pairs = [p.split('=', maxsplit=1) for p in key_values]
        key_lists = {k: [] for k, v in pairs}
        [key_lists[k].append(v) for k, v in pairs]

        key_counts = {k: len(v) for k, v in key_lists.items()}
        key_max_count = max(key_counts.values())
        if any([True for k, c in key_counts.items() if 1 < c < key_max_count]):
            parser.error(f"All keys given multiple times must be given the same number of times:\n"
                         f"{'\n'.join(['{}: {}'.format(k, c) for k, c in key_counts.items() if 1 < c])}")

        results = []
        for i in range(key_max_count):
            d = dict()
            for k, values in key_lists.items():
                v = values[0] if len(values) == 1 else values[i]
                d[k] = v
            results.append(d)

        setattr(namespace, self.dest, results)


class StoreSingleKeyValuePairs(argparse.Action):
    r"""Store a dictionary of key-value pairs."""

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 key_values: list[str],
                 option_string: str | None = None) -> None:
        r"""Turn a list of 'KEY=VALUE' pairs into a dictionary.

        Each KEY can be defined once. If defined more than once, a message will
        print to standard error and the program will exit with status code 2.

        Parameters
        ----------
        parser
            ArgumentParser object that contains this action.
        namespace
            Namespace object returned by :py:meth:`argparse.ArgumentParser.parse_args`.
        key_values
            List of strings containing key-value pairs.
        option_string
            Option string used to invoke this action.
        """

        for kv in key_values:
            if "=" not in kv:
                parser.error(f"Invalid argument '{kv}'. Expected key-value pairs '<key>=<value>'.")

        pairs = [p.split('=', maxsplit=1) for p in key_values]
        results = dict()
        for k, v in pairs:
            if k in results:
                parser.error(f"Duplicate key '{k}' found.\n"
                             f"Keys must not be given multiple times.")

            results[k] = v

        setattr(namespace, self.dest, results)


class StoreMatchOption(argparse.Action):
    r"""Store match statements and retain their order across multiple invocations."""

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 keys: list[str],
                 option_string: str | None = None) -> None:
        r"""Store a list of match statements in a list.

        This way multiple invocations of ``--match``  won't have their lists
        merged together, and can be considered independently of one another
        (i.e. ``OR``).

        Parameters
        ----------
        parser
            ArgumentParser object that contains this action.
        namespace
            Namespace object returned by :py:meth:`argparse.ArgumentParser.parse_args`.
        keys
            List of strings containing match statements.
        option_string
            Option string used to invoke this action.
        """

        items = getattr(namespace, self.dest, None)
        items = list() if items is None else items
        items.append(keys)

        setattr(namespace, self.dest, items)


class StoreSortOption(argparse.Action):
    r"""Store keys-to-sort and retain their order across multiple invoking options.

    The results destination is hardcoded to ``sort``. This allows multiple
    argparse options to use this action and retain the order of arguments passed
    at the CLI across option flags.
    """

    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str | None = None,
                 sort_direction: Literal['ascending', 'descending'] = 'ascending',
                 **kwargs) -> None:
        r"""Instantiate a ``StoreSortOption`` with its sort direction.

        The ``dest`` attribute is ignored and is hardcoded to ``'sort'``.

        The ``default`` attribute is incompatible with this Action, as it's not
        possible to know when to use/vs discard the default across multiple
        options.

        Parameters
        ----------
        option_strings
            List of option strings to associate with this action.
            Passed to :py:meth:`argparse.Action`
        dest
            This attribute is ignored and is hardcoded to ``'sort'``.
        sort_direction
            Sort direction.
        **kwargs
            Passed to :py:meth:`argparse.Action`

        Raises
        ------
        ValueError
            The ``default`` attribute is used.
        """

        if 'default' in kwargs.keys():
            raise ValueError("'default' must not be used with `StoreSortOption`")

        self._sorting = sort_direction

        super().__init__(option_strings, "sort", **kwargs)

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 keys: list[str],
                 option_string: str | None = None) -> None:
        r"""Store keys in a dictionary with the associated sort direction.

        Parameters
        ----------
        parser
            ArgumentParser object that contains this action.
        namespace
            Namespace object returned by :py:meth:`argparse.ArgumentParser.parse_args`.
        keys
            List of strings containing keys to sort.
        option_string
            Option string used to invoke this action.
        """

        partial_dict = {k: self._sorting for k in keys}

        items = getattr(namespace, self.dest, None)
        items = dict() if items is None else items
        items.update(partial_dict)

        setattr(namespace, self.dest, items)
