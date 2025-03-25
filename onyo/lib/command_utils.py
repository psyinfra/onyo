from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from onyo.lib.consts import (
    SORT_DESCENDING,
)
from onyo.lib.inventory import (
    Inventory,
    InventoryOperation,
)
from onyo.lib.ui import ui

if TYPE_CHECKING:
    from typing import (
        Sequence,
        Tuple,
    )
    from onyo.lib.consts import sort_t
    from onyo.lib.items import Item

log: logging.Logger = logging.getLogger('onyo.command_utils')


def allowed_config_args(git_config_args: list[str]) -> bool:
    r"""Check a list of arguments for disallowed ``git config`` flags.

    ``git-config`` stores configuration information in a variety of locations
    using location flags (e.g. ``--system``). Onyo uses ``--file`` to write to
    :py:data:`onyo.lib.consts.ONYO_CONFIG`.

    This function makes sure that such flags (and ``--help``) aren't in the
    list.

    A helper for py:func:`onyo.lib.commands.onyo_config`.

    Parameters
    ----------
    git_config_args
        List of arguments to pass to ``git config``.

    Raises
    ------
    ValueError
        A disallowed flag is detected.
    """

    forbidden_flags = ['--system', '--global', '--local', '--worktree',
                       '--file', '--blob',
                       '--help', '-h']
    if any([x in forbidden_flags for x in git_config_args]):
        raise ValueError("The following options cannot be used with onyo config:\n%s\nExiting. Nothing was set." %
                         '\n'.join(forbidden_flags))

    return True


def inline_path_diff(source: str | Path,
                     destination: str| Path) -> str:
    r"""Generate an inline diff of two paths.

    A **rename** (i.e. changing the last element) is its own action, and does
    not group with other changes. A **move** groups with adjacent changes when
    possible (e.g. a/b/c/d/one -> a/b/two: "a/{b/c/d -> b}/{one -> two}").

    Parameters
    ----------
    source
        Path of source.
    destination
        Path of destination.
    """

    if Path(source).is_absolute() or Path(destination).is_absolute():
        raise ValueError("Paths must be relative.")

    result = []

    s_parts = Path(source).parts
    d_parts = Path(destination).parts

    # Special case
    # No grouping is possible if either is one element long.
    if len(s_parts) == 1 or len(d_parts) == 1:
        return f"{'/'.join(s_parts)} -> {'/'.join(d_parts)}"

    #
    # Rename
    #
    # build suffix
    if s_parts[-1] == d_parts[-1]:
        suffix = s_parts[-1]
    else:
        suffix = f"{{{s_parts[-1]} -> {d_parts[-1]}}}"
    s_parts = s_parts[:-1]
    d_parts = d_parts[:-1]

    #
    # Move
    #
    while s_parts or d_parts:
        if s_parts[0] == d_parts[0]:
            # Either (but not both) would empty themselves.
            # So group all that is left.
            if (len(s_parts) == 1) ^ (len(d_parts) == 1):
                result.append(f"{{{'/'.join(s_parts)} -> {'/'.join(d_parts)}}}")
                break
            else:
                result.append(s_parts[0])
                s_parts = s_parts[1:]
                d_parts = d_parts[1:]
        else:
            # get the indexes of the /next/ mutual value
            ns, ds = intersect_index(s_parts[1:], d_parts[1:])
            ns = ns if ns is None else ns + 1 # correct index
            ds = ds if ds is None else ds + 1 # correct index

            if ns is None:
                # No more overlap between the two lists.
                # So group all that is left.
                result.append(f"{{{'/'.join(s_parts)} -> {'/'.join(d_parts)}}}")
                break
            else:
                # There is a future overlap. So group up until it.
                result.append(f"{{{'/'.join(s_parts[:ns])} -> {'/'.join(d_parts[:ds])}}}")
                s_parts = s_parts[ns:]
                d_parts = d_parts[ds:]

    result.append(suffix)

    return '/'.join(result)


def intersect_index(seq1: Sequence,
                    seq2: Sequence) -> Tuple[int | None, int | None]:
    r"""Get the indexes of the first matching value of two sequences.

    Returns ``None`` as the indexes if no match is found.

    Parameters
    ----------
    seq1
        First sequence
    seq2
        Second sequence
    """

    for index1, item in enumerate(seq1):
        try:
            index2 = seq2.index(item)
            return (index1, index2)
        except ValueError:
            pass

    return (None, None)


def natural_sort(items: list[Item],
                 keys: dict[str, sort_t]) -> list[Item]:
    r"""Sort ``items`` according to a list of ``keys``.

    Parameters
    ----------
    items
        Items to sort.
    keys
        Keys to sort ``items`` by.
    reverse
        Sort in reverse order.
    """

    import locale
    import natsort

    from onyo.lib.items import resolve_alias

    # set the locale for all categories to the user’s default setting
    locale.setlocale(locale.LC_ALL, '')

    for key in reversed(keys.keys()):
        alg = natsort.ns.LOCALE | natsort.ns.INT
        if resolve_alias(key).startswith('onyo.path'):
            alg |= natsort.ns.PATH
        items = sorted(items,
                       key=natsort.natsort_keygen(key=lambda x: x.get(key), alg=alg),
                       reverse=keys[key] == SORT_DESCENDING)

    return items


def print_diff(diffable: Inventory | InventoryOperation) -> None:
    r"""Print colorized diffs.

    The lines resulting from the object's ``diff()`` are colorized, with red or
    green corresponding to whether lines are removed or added.

    Parameters
    ----------
    diffable
        The object to print the diff of.
    """

    # This isn't nice yet. We need to consolidate `UI` to deal with that.
    # However, that requires figuring how to deal with issues, when
    # capturing output in tests and rich not realizing that.
    for line in diffable.diff():
        match line[0] if line else '':
            case '+':
                style = "green"
            case '-':
                style = "red"
            case '@':
                style = "bold"
            case _:
                style = ""

        ui.rich_print(line, style=style)


def inventory_path_to_yaml(inventory: Inventory,
                           path: Path,
                           recursive: bool = False,
                           base: Path | None = None) -> str:
    r"""Generate Onyo-YAML records of an inventory Path.

    Parameters
    ----------
    inventory
        The inventory to operate on.
    path
        Path to generate YAML of.
    recursive
        Descend recursively under ``path``.
    base
        Absolute path that ``onyo.path.parent`` keys are relative to.
    """

    from onyo.lib.consts import SORT_ASCENDING
    from onyo.lib.pseudokeys import PSEUDO_KEYS

    base = base or (path.parent if path != inventory.root else inventory.root)
    stream_uuid = uuid.uuid4()
    docid_table = {}

    items = list(inventory.get_items(
                     include=[path],
                     depth=0 if recursive else 1,
                     types=['assets', 'directories'],
                     intermediates=False)
            )
    items = natural_sort(items=items, keys={'onyo.path.relative': SORT_ASCENDING})  # pyre-ignore[6]

    # ensure that everything has a name or a document ID
    for item in items:
        if item["onyo.is.directory"]:
            if item["onyo.is.asset"]:
                # Asset directories require a unique ID so that children can use
                # a match statement to declare what record is their `onyo.path.parent`.
                # This uses the relative path in the repo as a unique label guaranteed by the FS.
                item["onyo.documentid"] = str(uuid.uuid5(stream_uuid, str(item["onyo.path.relative"])))
                docid_table[item["onyo.path.relative"]] = item["onyo.documentid"]
            else:
                # directory: trigger evaluation of the name pseudokey
                item.get("onyo.path.name")

    # build 'onyo.path.parent' (string or match a document ID)
    for item in items:
        if item["onyo.path.absolute"] == path:
            # top-level
            item["onyo.path.parent"] = str((inventory.root / item["onyo.path.parent"]).relative_to(base))
            continue

        if item["onyo.path.parent"] in docid_table:
            item["onyo.path.parent"] = f"<?onyo.documentid={docid_table[item['onyo.path.parent']]}>"
        else:
            item["onyo.path.parent"] = str((inventory.root / item["onyo.path.parent"]).relative_to(base))

    # strip most pseudokeys
    for item in items:
        for key in list(PSEUDO_KEYS.keys()):
            match key:
                case "onyo.is.asset" | "onyo.is.directory" | "onyo.path.parent":
                    # keep
                    continue
                case "onyo.path.name" if item["onyo.is.asset"]:
                    # remove asset path name --- names are generated
                    del item[key]
                case _:
                    # remove all other pseudo-keys
                    del item[key]

        del item["onyo.was"]

    # dump YAML
    return ''.join([i.yaml(exclude=[]) for i in items])

def iamyourfather(inventory: Inventory,
                  yaml_stream: str,
                  base: Path | None = None) -> list[Item]:

    from onyo.lib.utils import yaml_to_dict_multi
    from onyo.lib.filters import Filter
    from onyo.lib.items import Item

    specs = [d for d in yaml_to_dict_multi(yaml_stream)]
    for spec in specs:
        if spec["onyo.is.asset"]:
            spec["onyo.path.name"] = inventory.generate_asset_name(spec)
    for spec in specs:
        if not spec["onyo.path.parent"].startswith("<?") or not spec["onyo.path.parent"].endswith(">"):
            spec["onyo.path.parent"] = Path(spec["onyo.path.parent"])
            spec["onyo.path.relative"] = spec["onyo.path.parent"] / spec["onyo.path.name"]
    for spec in specs:
        if isinstance(spec["onyo.path.parent"], str) and spec["onyo.path.parent"].startswith("<?") and spec["onyo.path.parent"].endswith(">"):
            filter_ = Filter(spec["onyo.path.parent"][2:-1])
            matches = [s for s in specs if filter_.match(s)]
            assert len(matches) == 1
            spec["onyo.path.parent"] = matches[0]["onyo.path.relative"]
            spec["onyo.path.relative"] = spec["onyo.path.parent"] / spec["onyo.path.name"]

            # maybe put Filter.match in here and search for callables when resolving.
    return [Item(spec) for spec in specs]
