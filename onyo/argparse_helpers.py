from __future__ import annotations

import argparse
import os
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
        if any([True for k, c in key_counts.items() if 1 < c < key_max_count]):
            parser.error(f"All keys given multiple times must be given the same number of times:{os.linesep}"
                         f"{f'{os.linesep}'.join(['{}: {}'.format(k, c) for k, c in key_counts.items() if 1 < c])}")

        def cvt(v: str) -> int | float | str | bool:
            if v.lower() == "true":
                return True
            elif v.lower() == "false":
                return False
            try:
                r = int(v)
            except ValueError:
                try:
                    r = float(v)
                except ValueError:
                    r = v
            return r

        results = []
        for i in range(key_max_count):
            d = dict()
            for k, values in key_lists.items():
                v = values[0] if len(values) == 1 else values[i]
                d[k] = cvt(v)
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

        def cvt(v: str) -> int | float | str | bool:
            if v.lower() == "true":
                return True
            elif v.lower() == "false":
                return False
            try:
                r = int(v)
            except ValueError:
                try:
                    r = float(v)
                except ValueError:
                    r = v
            return r

        pairs = [p.split('=', maxsplit=1) for p in key_values]
        results = dict()
        for k, v in pairs:
            if k in results:
                parser.error(f"Duplicate key '{k}' found.{os.linesep}"
                             f"Keys must not be given multiple times.")

            results[k] = cvt(v)

        setattr(namespace, self.dest, results)
