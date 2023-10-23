import argparse
import os

from typing import Optional, Sequence, Union


class StoreKeyValuePairs(argparse.Action):
    def __init__(self,
                 option_strings: Sequence[str],
                 dest: str,
                 nargs: Union[None, int, str] = None,
                 **kwargs) -> None:
        self._nargs = nargs
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 key_values: list[str],
                 option_string: Optional[str] = None) -> None:
        """Turn a list of 'key=value' pairs into a list of dictionaries

        Every key appearing multiple times in `key=value` is applied to a new dictionary every time.
        All keys appearing multiple times, must appear the same number of times (and thereby define the number of dicts
        to be created). In case of different counts: raise.
        Every key appearing once in `key_values` will be applied to all dictionaries.
        """

        for kv in key_values:
            if "=" not in kv:
                parser.error(f"Invalid argument '{kv}'. Expected key-value pairs '<key>=<value>'.")
        pairs = [p.split('=', maxsplit=1) for p in key_values]
        register_dict = {k: [] for k, v in pairs}
        [register_dict[k].append(v) for k, v in pairs]
        number_of_dicts = max(len(v) for v in register_dict.values())
        invalid_keys = [(k, len(v)) for k, v in register_dict.items() if 1 < len(v) < number_of_dicts]
        if invalid_keys:
            parser.error(f"All keys given multiple times must be provided the same number of times."
                         f"Max. times a key was given: {number_of_dicts}.{os.linesep}"
                         f"But also got: {', '.join(['{} {} times'.format(k, c) for k, c in invalid_keys])}")

        def cvt(v: str) -> Union[int, float, str]:
            try:
                r = int(v)
            except ValueError:
                try:
                    r = float(v)
                except ValueError:
                    r = v
            return r

        results = []
        for i in range(number_of_dicts):
            d = dict()
            for k, values in register_dict.items():
                v = values[0] if len(values) == 1 else values[i]
                d[k] = cvt(v)
            results.append(d)
        setattr(namespace, self.dest, results)


def parse_key_values(string):
    """
    Convert a string of key-value pairs to a dictionary.

    The shell interprets the key-value string before it is passed to argparse.
    As a result, no quotes are passed through, but the chunking follows what the
    quoting declared.

    Because of the lack of quoting, this function cannot handle a comma in
    either the key or value.
    """
    results = {k: v for k, v in (pair.split('=') for pair in string.split(','))}
    for k, v in results.items():
        try:
            results.update({k: int(v)})
        except ValueError:
            try:
                results.update({k: float(v)})
            except ValueError:
                pass

    return results


def directory(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def file(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def git_config(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def path(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string


def template(string: str) -> str:
    """
    A no-op type-check for ArgParse. Used to hint for shell tab-completion.
    """
    return string
