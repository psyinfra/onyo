import argparse
from typing import Optional, Sequence, Union


class StoreKeyValuePairs(argparse.Action):
    def __init__(self, option_strings: Sequence[str], dest: str,
                 nargs: Union[None, int, str] = None, **kwargs) -> None:
        self._nargs = nargs
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace, key_values: list[str],
                 option_string: Optional[str] = None) -> None:
        results = {}
        for pair in key_values:
            k, v = pair.split('=', maxsplit=1)
            try:
                v = int(v)
            except ValueError:
                try:
                    float(v)
                except ValueError:
                    pass
            results[k] = v
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
