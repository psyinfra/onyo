from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Sequence


class StoreMultipleKeyValuePairs(argparse.Action):
    r"""Store a list of dictionaries of key-value pairs.

    See Also
    --------
    StoreSingleKeyValuePairs
    """

    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str,
                 nargs: int | str | None = None,
                 **kwargs) -> None:
        r"""
        Parameters
        ----------
        option_strings
        dest
        nargs
        **kwargs
        """
        self._nargs = nargs
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 key_values: list[str],
                 option_string: str | None = None) -> None:
        r"""Turn a list of 'KEY=VALUE' pairs into a list of dictionaries.

        Each KEY can be defined either 1 or N times (where N is the number of
        dictionaries to be created).

        A KEY that is declared once will apply to all dictionaries.

        All KEYs appearing N times must appear the same number of times. If not,
        a message will print to standard error and the program will exit with
        status code 2.

        Parameters
        ----------
        parser
        namespace
        key_values
            List of strings containing key-value pairs.
        option_string
        """

        for kv in key_values:
            if "=" not in kv:
                parser.error(f"Invalid argument '{kv}'. Expected key-value pairs '<key>=<value>'.")

        pairs = [p.split('=', maxsplit=1) for p in key_values]
        key_lists = {k: [] for k, v in pairs}
        [key_lists[k].append(v) for k, v in pairs]

        key_counts = {k: len(v) for k, v in key_lists.items()}
        key_max_count = max(key_counts.values())
        # Python < 3.12 does not support backslashes in f-strings
        linesep = '\n'
        if any([True for k, c in key_counts.items() if 1 < c < key_max_count]):
            parser.error(f"All keys given multiple times must be given the same number of times:\n"
                         f"{f'{linesep}'.join(['{}: {}'.format(k, c) for k, c in key_counts.items() if 1 < c])}")

        results = []
        for i in range(key_max_count):
            d = dict()
            for k, values in key_lists.items():
                v = values[0] if len(values) == 1 else values[i]
                d[k] = v
            results.append(d)
        setattr(namespace, self.dest, results)


class StoreSingleKeyValuePairs(argparse.Action):
    r"""Store a dictionary of key-value pairs.

    See Also
    --------
    StoreMultipleKeyValuePairs
    """

    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str,
                 nargs: int | str | None = None,
                 **kwargs) -> None:
        r"""
        Parameters
        ----------
        option_strings
        dest
        nargs
        **kwargs
        """
        self._nargs = nargs
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

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
        namespace
        key_values
            List of strings containing key-value pairs.
        option_string
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


class StoreSortOption(argparse.Action):

    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str,
                 **kwargs) -> None:
        r"""
        Parameters
        ----------
        option_strings
        dest
        **kwargs
        """
        # This is a hack.
        # We want sorting options where -s and -S take keys (to sort by) while
        # capitalization determines whether it's ascending or descending order.
        # Both are supposed to be intermixable.
        # For a proper specification and help for both options, they need to be
        # defined separately. But if we want to keep order in the intermixed case,
        # they need to be stored into the same object to maintain order.
        # Our way of specifying `dest` as the key in a dict defining the options
        # per command, prevents that, though.
        # With this hack we ignore the generated `dest` and set it to a fixed 'sort'.
        if 'default' in kwargs.keys():
            # We can't deal with defaults while accounting for two different
            # arguments, b/c we don't know when to discard the default.
            raise ValueError("'default' must not be used with `StoreSortOption`")
        for option in option_strings:
            if option.startswith('--sort-'):
                self._sorting = option[7:]
        super().__init__(option_strings, "sort", **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        partial_dict = {k: self._sorting for k in values}
        items = getattr(namespace, self.dest, None)
        items = dict() if items is None else items
        items.update(partial_dict)
        setattr(namespace, self.dest, items)
