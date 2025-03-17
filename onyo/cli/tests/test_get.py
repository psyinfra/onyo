from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from onyo.lib.consts import (
    SORT_ASCENDING,
    SORT_DESCENDING,
)
from onyo.lib.onyo import OnyoRepo
from onyo.lib.command_utils import natural_sort
from onyo.lib.items import (
    Item,
    ItemSpec,
)

if TYPE_CHECKING:
    from typing import (
        Any,
        Generator,
    )
    from onyo.lib.consts import sort_t


def convert_contents(
        raw_assets: list[tuple[str, dict[str, Any]]]) -> Generator:
    r"""Convert content dictionary to a plain-text string."""

    for file, raw_contents in raw_assets:
        yield [file, Item(raw_contents).yaml()]


tag_asset_contents = [
    ('type_make_model.1', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '1', 'key': True,
    }),
    ('type_make_model.2', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '2', 'key': False,
    }),
    ('type_make_model.3', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '3', 'key': None,
    }),
    ('type_make_model.4', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '4',
    }),
    ('type_make_model.5', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '5', 'key': 'value',
    }),
    ('type_make_model.6', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '6', 'key': '',
    }),
    ('type_make_model.7', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '7', 'key': ['a', 'b'],
    }),
    ('type_make_model.8', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '8', 'key': [],
    }),
    ('type_make_model.9', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '9', 'key': {'a': '1', 'b': '2'},
    }),
    ('type_make_model.10', {
        'type': 'type', 'make': 'make', 'model': 'model', 'serial': '10', 'key': {},
    }),
]


@pytest.mark.repo_contents(*convert_contents(tag_asset_contents))
def test_get_tag_output(repo: OnyoRepo) -> None:
    r"""Query with tags and check output.

    Only a subset of tags are used in the output. The rest are only for queries.
    """

    cmd = ['onyo', 'get', '--machine-readable', '--keys', 'onyo.path.relative', 'key', '--sort-ascending', 'onyo.path.relative']

    #
    # all
    #
    ret = subprocess.run(cmd, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.1	True\n"
        "type_make_model.2	False\n"
        "type_make_model.3	<null>\n"
        "type_make_model.4	<unset>\n"
        "type_make_model.5	value\n"
        "type_make_model.6	\n"
        "type_make_model.7	<list>\n"
        "type_make_model.8	<list>\n"
        "type_make_model.9	<dict>\n"
        "type_make_model.10	<dict>\n"
    )
    assert expected_output == ret.stdout

    #
    # <bool>
    #
    match = ['--match', 'key=<bool>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.1	True\n"
        "type_make_model.2	False\n"
    )
    assert expected_output == ret.stdout

    #
    # <dict>
    #
    match = ['--match', 'key=<dict>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.9	<dict>\n"
        "type_make_model.10	<dict>\n"
    )
    assert expected_output == ret.stdout

    #
    # <empty>
    #
    match = ['--match', 'key=<empty>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.3	<null>\n"
        "type_make_model.6	\n"
        "type_make_model.8	<list>\n"
        "type_make_model.10	<dict>\n"
    )
    assert expected_output == ret.stdout

    #
    # <false>
    #
    match = ['--match', 'key=<false>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.2	False\n"
    )
    assert expected_output == ret.stdout

    #
    # <null>
    #
    match = ['--match', 'key=<null>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.3	<null>\n"
    )
    assert expected_output == ret.stdout

    #
    # <true>
    #
    match = ['--match', 'key=<true>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.1	True\n"
    )
    assert expected_output == ret.stdout

    #
    # <unset>
    #
    match = ['--match', 'key=<unset>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "type_make_model.4	<unset>\n"
    )
    assert expected_output == ret.stdout


match_asset_contents = [
    ('laptop_apple_model.1', {
        'type': 'laptop', 'make': 'apple', 'model': 'model', 'serial': '1',
    }),
    ('laptop_apple_model.2', {
        'type': 'laptop', 'make': 'apple', 'model': 'model', 'serial': '2',
    }),
    ('laptop_framework_model.3', {
        'type': 'laptop', 'make': 'framework', 'model': 'model', 'serial': '3',
    }),
    ('laptop_framework_model.4', {
        'type': 'laptop', 'make': 'framework', 'model': 'model', 'serial': '4',
    }),
    ('display_dell_model.5', {
        'type': 'display', 'make': 'dell', 'model': 'model', 'serial': '5', 'key': True,
    }),
    ('display_dell_model.6', {
        'type': 'display', 'make': 'dell', 'model': 'model', 'serial': '6',
    }),
    ('display_eizo_model.7', {
        'type': 'display', 'make': 'eizo', 'model': 'model', 'serial': '7',
    }),
    ('display_eizo_model.8', {
        'type': 'display', 'make': 'eizo', 'model': 'model', 'serial': '8',
    }),
    ('headphones_sennheiser_model.9', {
        'type': 'headphones', 'make': 'sennheiser', 'model': 'model', 'serial': '9', 'key': 'value',
    }),
    ('headphones_sennheiser_model.10', {
        'type': 'headphones', 'make': 'sennheiser', 'model': 'model', 'serial': '10',
    }),
]


@pytest.mark.repo_contents(*convert_contents(match_asset_contents))
def test_get_complex_match(repo: OnyoRepo) -> None:
    r"""Multiple argument are passed to multiple match statements."""

    cmd = ['onyo', 'get', '--machine-readable', '--keys', 'onyo.path.relative', 'key', '--sort-ascending', 'serial']

    #
    # all
    #
    ret = subprocess.run(cmd, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "laptop_apple_model.1	<unset>\n"
        "laptop_apple_model.2	<unset>\n"
        "laptop_framework_model.3	<unset>\n"
        "laptop_framework_model.4	<unset>\n"
        "display_dell_model.5	True\n"
        "display_dell_model.6	<unset>\n"
        "display_eizo_model.7	<unset>\n"
        "display_eizo_model.8	<unset>\n"
        "headphones_sennheiser_model.9	value\n"
        "headphones_sennheiser_model.10	<unset>\n"
    )
    assert expected_output == ret.stdout

    #
    # complex subset
    #
    match = ['--match', 'type=laptop', 'make=framework', '--match', 'type=display', 'make=eizo', '--match', 'key=<true>']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "laptop_framework_model.3	<unset>\n"
        "laptop_framework_model.4	<unset>\n"
        "display_dell_model.5	True\n"
        "display_eizo_model.7	<unset>\n"
        "display_eizo_model.8	<unset>\n"
    )
    assert expected_output == ret.stdout

    #
    # overlapping matches (ensure no duplicates)
    #
    match = ['--match', 'type=headphones', 'key!=<unset>', '--match', 'type=headphones', 'make=sennheiser', '--match', 'make=eizo']
    ret = subprocess.run(cmd + match, capture_output=True, text=True)

    assert ret.returncode == 0
    assert not ret.stderr

    expected_output = (
        "display_eizo_model.7	<unset>\n"
        "display_eizo_model.8	<unset>\n"
        "headphones_sennheiser_model.9	value\n"
        "headphones_sennheiser_model.10	<unset>\n"
    )
    assert expected_output == ret.stdout


asset_contents = [
    ('laptop_apple_macbookpro.1', {'num': 8,
                                   'str': 'foo',
                                   'bool': True,
                                   'type': 'laptop',
                                   'make': 'apple',
                                   'model': {'name': 'macbookpro'},
                                   'serial': '1'}),
    ('one/laptop_dell_precision.2', {'num': '16',
                                     'str': 'bar',
                                     'bool': False,
                                     'type': 'laptop',
                                     'make': 'dell',
                                     'model': {'name': 'precision'},
                                     'serial': '2'}),
    ('one/two/headphones_apple_pro.3', {'num': '8',
                                        'str': 'bar',
                                        'bool': 'True',
                                        'type': 'headphones',
                                        'make': 'apple',
                                        'model': {'name': 'pro'},
                                        'serial': '3'}),
    ('abc/def/monitor_dell_pro.4', {'str': 'foo=bar',
                                    'type': 'monitor',
                                    'make': 'dell',
                                    'model': {'name': 'pro'},
                                    'serial': '4'}),
    ('laptop_dell_precision.2', {'num': '16',
                                 'str': 'bar',
                                 'bool': False,
                                 'type': 'laptop',
                                 'make': 'dell',
                                 'model': {'name': 'precision'},
                                 'serial': '2'}),
    ('headphones_apple_pro.3', {'num': '8',
                                'str': 'bar',
                                'bool': 'True',
                                'type': 'headphones',
                                'make': 'apple',
                                'model': {'name': 'pro'},
                                'serial': '3'}),
    ('monitor_dell_pro.4', {'str': 'foo=bar',
                            'type': 'monitor',
                            'make': 'dell',
                            'model': {'name': 'pro'},
                            'serial': '4'}),
    ('headphones_dell_pro.4', {'num': '10GB',
                               'str': 'bar',
                               'type': 'headphones',
                               'make': 'dell',
                               'model': {'name': 'pro'},
                               'serial': '4'}),
    ('one/two/three/headphones_apple_pro.4', {'type': 'headphones',
                                              'make': 'apple',
                                              'model': {'name': 'pro'},
                                              'serial': '4'}),
    ('one/two/three/four/headphones_apple_pro.5', {'type': 'headphones',
                                                   'make': 'apple',
                                                   'model': {'name': 'pro'},
                                                   'serial': '5'}),
    ('another/dir/headphones_apple_pro.5', {'type': 'headphones',
                                            'make': 'apple',
                                            'model': {'name': 'pro'},
                                            'serial': '5'}),
    ('a13bc_foo_bar.1', {'num': 'num-3',
                         'type': 'a13bc',
                         'make': 'foo',
                         'model': {'name': 'bar'},
                         'serial': '1',
                         'str': 'abc',
                         'id': 1}),
    ('a2cd_foo_bar.2', {'num': 'num-16',
                        'type': 'a2cd',
                        'make': 'foo',
                        'model': {'name': 'bar'},
                        'serial': '2',
                        'str': 'def',
                        'id': 2}),
    ('a36ab_foo_bar.3', {'num': 'num-20',
                         'type': 'a36ab',
                         'make': 'foo',
                         'model': {'name': 'bar'},
                         'serial': '3',
                         'str': 'ghi',
                         'id': 3}),
    ('a36ab_afoo_bar.4', {'num': 'num-20',
                          'type': 'a36ab',
                          'make': 'afoo',
                          'model': {'name': 'bar'},
                          'serial': '4',
                          'str': 'jkl',
                          'id': 4}),
]


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3']]))
def test_get_defaults(repo: OnyoRepo) -> None:
    r"""Test ``onyo get`` using default values."""

    cmd = ['onyo', 'get']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    keys = ['type', 'make', 'model.name', 'serial', 'onyo.path.relative']
    assert 'laptop_apple_macbookpro.1' in ret.stdout
    assert 'laptop_dell_precision.2' in ret.stdout
    assert 'headphones_apple_pro.3' in ret.stdout
    assert all([key in ret.stdout for key in keys])
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3',
                                                          'abc/def/monitor_dell_pro.4']]))
@pytest.mark.parametrize('matches', [['str=bar', 'type=laptop'], []])
@pytest.mark.parametrize('depth', ['0', '1', '2'])
@pytest.mark.parametrize('keys', [
    [], ['make', 'serial'], ['num', 'str', 'bool']])
@pytest.mark.parametrize('paths', [['.'], ['one/two', 'abc/def']])
@pytest.mark.parametrize('machine_readable', ['-H', None])
def test_get_all(repo: OnyoRepo,
                 matches: list[str],
                 depth: str,
                 keys: list[str],
                 paths: list[str],
                 machine_readable: str | None) -> None:
    r"""Test ``onyo get`` with a combination of valid arguments to ensure no error occurs."""

    keys = keys if keys else repo.get_asset_name_keys()
    cmd = ['onyo', 'get', '--include', *paths, '--depth', depth]
    cmd += ['--keys', *keys + ["onyo.path.relative"]] if keys else []
    cmd += ['--match', *matches] if matches else []
    cmd += [machine_readable] if machine_readable else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]
    init_paths = set(Path(path) for path in paths)

    if machine_readable:
        for line in output:
            # match
            for f in matches:
                key, value = f.split('=', 1)
                if key in keys:  # we cannot test unrequested keys
                    assert line[keys.index(key)] == value

            assert len(line) == len(keys) + 1  # +1 to include path

            if init_paths:
                assert any(init_paths & set(Path(line[-1]).parents))

    assert not ret.stderr
    # exit of 0 means results found and 1 no results found
    # exit of 2 means error
    assert ret.returncode in [0, 1]


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'laptop_dell_precision.2',
                                                          'headphones_apple_pro.3',
                                                          'monitor_dell_pro.4']]))
@pytest.mark.parametrize('matches,expected', [
    (['type=laptop'], 2),
    (['str=bar', 'type=laptop'], 1),
    (['make=apple', 'str=bar'], 1),
    (['bool=True'], 2),
    (['bool=False'], 1),
    (['num=8'], 2),
    (['num=16'], 1),
    (['unset=foo'], 0),
    (['str=foo', 'unset=bar'], 0),
    (['str=foo=bar'], 1),
    ([], 4)])
def test_get_filter(repo: OnyoRepo,
                    matches: list[str],
                    expected: int) -> None:
    r"""``onyo get --match KEY=VALUE`` retrieves the expected files."""

    keys = repo.get_asset_name_keys() + ['num', 'str', 'bool', 'unset']
    cmd = ['onyo', 'get', '--keys', *keys, '-H']
    cmd += ['--match', *matches] if matches else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # assert that all values match
    for key in matches:
        key, value = key.split('=', 1)
        for line in output:
            assert line[keys.index(key)] == value

    assert len(output) == expected
    assert not ret.stderr
    if expected > 0:
        assert ret.returncode == 0
    else:
        # no results should exit with 1
        assert ret.returncode == 1


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'laptop_dell_precision.2',
                                                          'headphones_apple_pro.3',
                                                          'headphones_dell_pro.4']]))
@pytest.mark.parametrize('matches,expected', [
    (['type=lap'], 0),  # full-matches only
    (['type=lap.*'], 2),
    (['num=8.*'], 2),
    (['str=foo.*'], 1),
    ([r'num=9\d*|\d{1,}'], 3)])
def test_get_filter_regex(repo: OnyoRepo,
                          matches: list[str],
                          expected: int) -> None:
    r"""``onyo get --match KEY=VALUE`` retrieves the expected files matching a regex."""

    keys = repo.get_asset_name_keys() + ['num', 'str', 'bool', 'unset']
    cmd = ['onyo', 'get', '--match', *matches, '--keys', *keys, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # assert that all values match
    for key in matches:
        key, value = key.split('=', 1)
        r = re.compile(value)

        for line in output:
            assert r.match(line[keys.index(key)])

    assert len(output) == expected
    assert not ret.stderr
    if expected > 0:
        assert ret.returncode == 0
    else:
        # no results should exit with 1
        assert ret.returncode == 1


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'laptop_dell_precision.2',
                                                          'headphones_apple_pro.3']]))
@pytest.mark.parametrize('matches', [
    ['num'],
    ['']])
def test_get_filter_errors(repo: OnyoRepo,
                           matches: list[str]) -> None:
    r"""``onyo get --match KEY=VALUE`` returns an error if missing a value."""

    cmd = ['onyo', 'get', '--match', *matches, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)

    assert ret.stderr
    assert not ret.stdout
    assert ret.returncode == 2


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'laptop_dell_precision.2',
                                                          'headphones_apple_pro.3']]))
@pytest.mark.parametrize('raw_assets', [[t for t in asset_contents
                                         if t[0] in ['laptop_apple_macbookpro.1',
                                                     'laptop_dell_precision.2',
                                                     'headphones_apple_pro.3']]])
@pytest.mark.parametrize('keys', [
    ['type', 'make', 'model.name', 'serial', 'onyo.path.relative'],
    ['unset', 'type', 'unset2', 'make', 'onyo.path.relative'],
    ['num', 'str', 'bool', 'onyo.path.relative'],
    ['TyPe', 'MAKE', 'moDEL', 'NuM', 'STR', 'onyo.path.relative'],
    []])
def test_get_keys(repo: OnyoRepo,
                  raw_assets: list[tuple[str, dict[str, Any]]],
                  keys: list) -> None:
    r"""Test that ``onyo get --keys x y z`` retrieves the expected keys."""

    from onyo.lib.pseudokeys import PSEUDO_KEYS
    cmd = ['onyo', 'get', '-H']
    cmd += ['--keys', *keys, ] if keys else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # Asset name keys returned if no keys were specified
    if not keys:
        keys = repo.get_asset_name_keys() + ["onyo.path.relative"]

    # Get all the key values and make sure they match
    for line in output:
        asset = ItemSpec(raw_assets[[a[0] for a in raw_assets].index(line[-1])][1])

        for i, key in enumerate(keys):
            if key in PSEUDO_KEYS:
                continue
            # convert raw asset values to str because output type is str
            assert str(asset.get(key, '<unset>')) == line[i]

    assert len(output) == len(repo.asset_paths)
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3',
                                                          'one/two/three/headphones_apple_pro.4',
                                                          'one/two/three/four/headphones_apple_pro.5']]))
@pytest.mark.parametrize('depth,expected', [
    ('0', 5), ('1', 1), ('2', 2), ('3', 3), ('4', 4), ('999', 5)])
def test_get_depth(repo: OnyoRepo,
                   depth: str,
                   expected: int) -> None:
    r"""Test that ``onyo get --depth x`` retrieves the expected assets."""

    cmd = ['onyo', 'get', '--depth', depth, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # Ensure all listed assets have a path equal to or smaller than depth
    for line in output:
        # . is returned if 0 parents, hence `- 1`
        n_parents = len(Path(line[-1]).parents) - 1
        assert n_parents <= int(depth) if int(depth) != 0 else True

    assert len(output) == expected
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3',
                                                          'one/two/three/headphones_apple_pro.4',
                                                          'one/two/three/four/headphones_apple_pro.5']]))
def test_get_depth_error(repo: OnyoRepo) -> None:
    r"""``onyo get --depth x`` must be a non-negative integer."""

    cmd = ['onyo', 'get', '--depth', '-1', '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.stderr
    assert "depth must be greater or equal 0, but is '-1'" in ret.stderr
    assert ret.returncode == 2


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3',
                                                          'one/two/three/headphones_apple_pro.4',
                                                          'one/two/three/four/headphones_apple_pro.5',
                                                          'another/dir/headphones_apple_pro.5']]))
@pytest.mark.parametrize('paths,depth,expected', [
    (['./one'], '0', 4), (['./one'], '1', 1), (['./one'], '2', 2),
    (['./one/two/three', './another/dir'], '0', 3),
    (['./one/two/three', './another/dir'], '1', 2),
    (['./one/two/three', './another'], '2', 3),
    (['.'], '0', 6), (['.'], '1', 1), (['.'], '2', 2),
    (['./one'], None, 4),
    (['./one/two'], None, 3),
    (['./one/two/three'], None, 2),
    (['one/two/three'], None, 2),
    (['./one/two/three/four'], None, 1),
    (['.', './one', './one/two/three/four'], None, 6),
    (['./one/two/three/four', './another/dir'], None, 2),
    ([], None, 6)])
def test_get_path_at_depth(repo: OnyoRepo,
                           paths: str,
                           depth: str | None,
                           expected: int) -> None:
    r"""``--depth`` is relative to the given paths.

    A portion of the parameters tests the usage of path with the default value
    of depth, when no depth is specified.
    """

    cmd = ['onyo', 'get', '-H']
    cmd += ['--include', *paths] if paths else []
    cmd += ['--depth', depth] if depth else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # Ensure one of the given paths matches the outermost parents of each asset
    set_paths = set(Path(path) for path in paths)

    if set_paths:
        for line in output:
            assert any(set_paths & set(Path(line[-1]).parents))

    assert len(output) == expected
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3',
                                                          'one/two/three/headphones_apple_pro.4',
                                                          'one/two/three/four/headphones_apple_pro.5',
                                                          'another/dir/headphones_apple_pro.5']]))
@pytest.mark.parametrize('path', [
    '/one/two/three',
    './path/that/does/not/exist/but/is/very/long',
    '/path/that/does/not/exist/and/does/not/start/with/dot',
    'path/that/does/not/exist/and/does/not/start/with/dot/slash',
    'def/ghi'])
def test_get_path_error(repo: OnyoRepo,
                        path: str) -> None:
    r"""Error if an invalid path is passed to `--include``."""

    cmd = ['onyo', 'get', '--include', path, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert f"The following paths are not part of the inventory:\n{repo.git.root / path}" in ret.stderr
    assert ret.returncode == 2


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['a13bc_foo_bar.1',
                                                          'a2cd_foo_bar.2',
                                                          'a36ab_foo_bar.3',
                                                          'a36ab_afoo_bar.4']]))
@pytest.mark.parametrize('sort,expected_order', [
    (['-s', 'make',
      '-s', 'num'], [4, 1, 2, 3]),
    (['-S', 'make',
      '-s', 'type'], [2, 1, 3, 4])
])
def test_get_sort(repo: OnyoRepo,
                  sort: list[str],
                  expected_order: list[int]) -> None:
    r"""Test ``-s`` (ascending) and ``-S`` (descending) sorting options."""

    # Note: This test has fewer test cases than `test_natural_sort`
    #       below. This is b/c here we are testing CLI and rely on
    #       reading assets from a repository. That implies we
    #       don't know the original order of assets and thus testing
    #       sorting that doesn't touch some elements gets wild.
    #       However, this really only needs to test that the options
    #       work as expected and result in the right call to actual
    #       sorting, which is tested separately.
    cmd = ['onyo', 'get', '-H']
    cmd += ['--keys', 'id']
    cmd += sort
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    result = [int(line) for line in ret.stdout.splitlines()]
    assert result == expected_order


@pytest.mark.parametrize('keys,expected', [
    ({'num': SORT_ASCENDING}, [1, 2, 3, 4]),
    ({'num': SORT_DESCENDING}, [3, 4, 2, 1]),  # no difference for 3,4 -> order is stable
    ({'str': SORT_ASCENDING}, [1, 2, 3, 4]),
    ({'str': SORT_DESCENDING}, [4, 3, 2, 1]),
    ({'type': SORT_ASCENDING}, [2, 1, 3, 4]),
    ({'type': SORT_DESCENDING}, [3, 4, 1, 2]),  # no difference for 3,4 -> order is stable
    ({'model.name': SORT_ASCENDING}, [1, 2, 3, 4]),  # for 'model.name' all assets are equal -> order is stable
    ({'model.name': SORT_DESCENDING}, [1, 2, 3, 4]),  # same
    ({'make': SORT_ASCENDING,
      'num': SORT_ASCENDING}, [4, 1, 2, 3]),
    ({'make': SORT_DESCENDING,
      'type': SORT_ASCENDING}, [2, 1, 3, 4])
])
def test_natural_sort(keys: dict[str, sort_t],
                      expected: list[int]) -> None:
    r"""Test implementation of natural sorting algorithm."""

    assets = [ItemSpec(t[1]) for t in asset_contents
              if t[0] in ['a13bc_foo_bar.1',
                          'a2cd_foo_bar.2',
                          'a36ab_foo_bar.3',
                          'a36ab_afoo_bar.4']]
    sorted_assets = natural_sort(assets, keys=keys)  # pyre-ignore[6]
    # ^ No idea why this is the only place where pyre can't figure that ItemSpec is a UserDict
    assert expected == [data.get('id') for data in sorted_assets]

    # explicitly check path sorting:
    assets = [{'onyo.path.relative': Path('folder/file (1).txt')},
              {'onyo.path.relative': Path('folder/file.txt')},
              {'onyo.path.relative': Path('folder (1)/file.txt')},
              {'onyo.path.relative': Path('folder (10)/file.txt')}]
    sorted_assets = natural_sort(assets, {'onyo.path.relative': SORT_ASCENDING})  # pyre-ignore[6]
    expectation = ['folder/file.txt',
                   'folder/file (1).txt',
                   'folder (1)/file.txt',
                   'folder (10)/file.txt']
    assert expectation == [str(a.get('onyo.path.relative')) for a in sorted_assets]


@pytest.mark.repo_contents(*convert_contents([t for t in asset_contents
                                              if t[0] in ['laptop_apple_macbookpro.1',
                                                          'one/laptop_dell_precision.2',
                                                          'one/two/headphones_apple_pro.3']] +
                                             [('.onyo/templates/laptop_dell_precision',
                                               {'num': '16',
                                                'str': 'bar',
                                                'bool': False,
                                                'type': 'laptop',
                                                'make': 'dell',
                                                'model': {'name': 'precision'},
                                                'serial': 'faux'})]))
def test_get_types(repo: OnyoRepo):

    # get all assets, directories, and templates
    cmd = ['onyo', 'get', '-H', '--types', 'assets', 'directories', '--keys', 'onyo.path.relative',
           '--include', '.', '.onyo/templates']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    output_lines = ret.stdout.splitlines()
    assert len(output_lines) == 9
    # 3 assets (see decorator),
    # 3 templates (2 default + 1 from decorator),
    # 3 dirs (two from decorator + root)
    assert all(p in output_lines
               for p in [
                   '.',
                   'one',
                   'one/two',
                   '.onyo/templates',
                   '.onyo/templates/laptop.example',
                   '.onyo/templates/laptop_dell_precision',
                   'laptop_apple_macbookpro.1',
                   'one/laptop_dell_precision.2',
                   'one/two/headphones_apple_pro.3'
               ])

    # get a match across assets and templates:
    cmd = ['onyo', 'get', '-H', '--types', 'assets', 'directories', '--keys', 'onyo.path.relative',
           '--include', '.', '.onyo/templates', '--match', 'make=dell']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    output_lines = ret.stdout.splitlines()
    # 1 asset, 1 template, no dirs
    assert len(output_lines) == 2
    assert all(p in output_lines for p in ['one/laptop_dell_precision.2', '.onyo/templates/laptop_dell_precision'])

    # same match, but don't match templates:
    cmd = ['onyo', 'get', '-H', '--types', 'assets', 'directories', '--keys', 'onyo.path.relative',
           '--match', 'make=dell']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    output_lines = ret.stdout.splitlines()
    # 1 asset, no dirs
    assert len(output_lines) == 1
    assert all(p in output_lines for p in ['one/laptop_dell_precision.2'])

    # match across assets and dirs:
    cmd = ['onyo', 'get', '-H', '--types', 'assets', 'directories', '--keys', 'onyo.path.relative',
           '--match', 'onyo.path.parent=one']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.returncode == 0
    assert not ret.stderr
    output_lines = ret.stdout.splitlines()
    # 1 asset, 1 dir
    assert len(output_lines) == 2
    assert all(p in output_lines for p in ['one/laptop_dell_precision.2', 'one/two'])
