import re
import subprocess
from pathlib import Path
from typing import Any, Generator, Union

from onyo.commands.get import (
    natural_sort, fill_unset, set_filters, sanitize_keys)
from onyo.lib import Repo, Filter
import pytest


def convert_contents(
        raw_assets: list[tuple[str, dict[str, Any]]]) -> Generator:
    """Convert content dictionary to a plain-text string"""
    for file, raw_contents in raw_assets:
        contents = ''
        for k, v in raw_contents.items():
            if isinstance(v, str):
                v = f"'{v}'"
            elif isinstance(v, bool):
                v = str(v).lower()
            contents += f'{k}: {v}\n'
        yield [file, contents]


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1',
     {'num': 8, 'str': 'foo', 'bool': True}),
    ('one/laptop_dell_precision.2',
     {'num': '16', 'str': 'bar', 'bool': False}),
    ('one/two/headphones_apple_pro.3',
     {'num': '8', 'str': 'bar', 'bool': 'True'})]))
def test_get_defaults(repo: Repo) -> None:
    """Test `onyo get` using default values"""
    cmd = ['onyo', 'get']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    keys = ['type', 'make', 'model', 'serial', 'path']
    assert 'laptop_apple_macbookpro.1' in ret.stdout
    assert 'laptop_dell_precision.2' in ret.stdout
    assert 'headphones_apple_pro.3' in ret.stdout
    assert all([key in ret.stdout for key in keys])
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1',
     {'num': 8, 'str': 'foo', 'bool': True}),
    ('one/laptop_dell_precision.2',
     {'num': '16', 'str': 'bar', 'bool': False}),
    ('one/two/headphones_apple_pro.3',
     {'num': '8', 'str': 'bar', 'bool': 'True'}),
    ('abc/def/monitor_dell_pro.4', {'str': 'foo=bar'})]))
@pytest.mark.parametrize('filters', [['str=bar', 'type=laptop'], []])
@pytest.mark.parametrize('depth', ['0', '1', '2'])
@pytest.mark.parametrize('keys', [
    [], ['make', 'serial'], ['num', 'str', 'bool']])
@pytest.mark.parametrize('paths', [['.'], ['one/two', 'abc/def']])
@pytest.mark.parametrize('machine_readable', ['-H', None])
@pytest.mark.parametrize('sort', ['-s', None])
def test_get_all(
        repo: Repo, filters: list[str], depth: str, keys: list[str],
        paths: list[str], machine_readable: Union[str, None],
        sort: Union[str, None]) -> None:
    """
    Test `onyo get` with a combination of arguments.
    """
    keys = keys if keys else repo.pseudo_keys
    cmd = ['onyo', 'get', '--path', *paths, '--depth', depth]
    cmd += ['--keys', *keys] if keys else []
    cmd += ['--filter', *filters] if filters else []
    cmd += [machine_readable] if machine_readable else []
    cmd += [sort] if sort else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]
    init_paths = set(Path(path) for path in paths)

    if machine_readable:
        for line in output:
            # match filters
            for f in filters:
                key, value = f.split('=', 1)
                if key in keys:  # we cannot test unrequested keys
                    assert line[keys.index(key)] == value

            assert len(line) == len(keys) + 1  # +1 to include path

            if init_paths:
                assert any(init_paths & set(Path(line[-1]).parents))

    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1',
     {'num': 8, 'str': 'foo', 'bool': True}),
    ('laptop_dell_precision.2',
     {'num': '16', 'str': 'bar', 'bool': False}),
    ('headphones_apple_pro.3',
     {'num': '8', 'str': 'bar', 'bool': 'True'}),
    ('monitor_dell_pro.4', {'str': 'foo=bar'})]))
@pytest.mark.parametrize('filters,expected', [
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
def test_get_filter(
        repo: Repo, filters: list[str], expected: int) -> None:
    """
    Test that `onyo get --filter KEY=VALUE` retrieves the expected
    files.
    """
    keys = repo.pseudo_keys + ['num', 'str', 'bool', 'unset']
    cmd = ['onyo', 'get', '--keys', *keys, '-H']
    cmd += ['--filter', *filters] if filters else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # assert that all values match the filters
    for key in filters:
        key, value = key.split('=', 1)
        for line in output:
            assert line[keys.index(key)] == value

    assert len(output) == expected
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo'}),
    ('laptop_dell_precision.2', {'num': '16', 'str': 'foobar'}),
    ('headphones_apple_pro.3', {'num': '8GB', 'str': 'bar'}),
    ('headphones_dell_pro.4', {'num': '10GB', 'str': 'bar'})]))
@pytest.mark.parametrize('filters,expected', [
    (['type=lap'], 0),  # full-matches only
    (['type=lap.*'], 2),
    (['num=8.*'], 2),
    (['str=foo.*'], 2),
    ([r'num=9\d*|\d{1,}'], 2)])
def test_get_filter_regex(
        repo: Repo, filters: list[str], expected: int) -> None:
    """
    Test that `onyo get --filter KEY=VALUE` retrieves the expected
    files using a regular expression as value
    """
    keys = repo.pseudo_keys + ['num', 'str', 'bool', 'unset']
    cmd = ['onyo', 'get', '--filter', *filters, '--keys', *keys, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # assert that all values match the filters
    for key in filters:
        key, value = key.split('=', 1)
        r = re.compile(value)

        for line in output:
            assert r.match(line[keys.index(key)])

    assert len(output) == expected
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'})]))
@pytest.mark.parametrize('filters', [
    ['type=laptop', 'type=laptop'],
    ['type=laptop', 'type=headphones'],
    ['num=16', 'num=16'],
    ['num=8', 'num=16'],
    ['num=8.*', 'num=16.*'],
    ['num'],
    ['']])
def test_get_filter_errors(repo: Repo, filters: list[str]) -> None:
    """
    Test that `onyo get --filter KEY=VALUE` returns an error when using
    duplicate filter keys or missing a value
    """
    cmd = ['onyo', 'get', '--filter', *filters, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)

    assert ret.stderr
    assert not ret.stdout
    assert ret.returncode == 1


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'})]))
@pytest.mark.parametrize('raw_assets', [[
    ('laptop_apple_macbookpro.1', {'num': 8, 'str': 'foo', 'bool': True}),
    ('laptop_dell_precision.2', {'num': '16', 'str': 'bar', 'bool': False}),
    ('headphones_apple_pro.3', {'num': '8', 'str': 'bar', 'bool': 'True'})]])
@pytest.mark.parametrize('keys', [
    ['type', 'make', 'model', 'serial'],
    ['unset', 'type', 'unset2', 'make'],
    ['num', 'str', 'bool'],
    ['TyPe', 'MAKE', 'moDEL', 'NuM', 'STR'],
    []])
def test_get_keys(
        repo: Repo, raw_assets: list[tuple[str, dict[str, Any]]],
        keys: list) -> None:
    """
    Test that `onyo get --keys x y z` retrieves the expected keys.
    """
    cmd = ['onyo', 'get', '-H']
    cmd += ['--keys', *keys, ] if keys else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    # Pseudo keys returned if no keys were specified
    if not keys:
        keys = repo.pseudo_keys

    # Get all the key values and make sure they match
    for line in output:
        asset = raw_assets[[a[0] for a in raw_assets].index(line[-1])][1]

        # add type, make, model, serial from asset name
        asset = asset | dict(zip(
            ['type', 'make', 'model', 'serial'],
            re.split('[_.]', Path(line[-1]).name)))

        for i, key in enumerate(keys):
            # convert raw asset values to str because output type is str
            assert str(asset.get(key, '<unset>')) == line[i]

    assert len(output) == len(repo.assets)
    assert not ret.stderr
    assert ret.returncode == 0


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {}),
    ('one/laptop_dell_precision.2', {}),
    ('one/two/headphones_apple_pro.3', {}),
    ('one/two/three/headphones_apple_pro.4', {}),
    ('one/two/three/four/headphones_apple_pro.5', {})]))
@pytest.mark.parametrize('depth,expected', [
    ('0', 5), ('1', 1), ('2', 2), ('3', 3), ('4', 4), ('999', 5)])
def test_get_depth(repo: Repo, depth: str, expected: int) -> None:
    """
    Test that `onyo get --depth x` retrieves the expected assets.
    """
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


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {}),
    ('one/laptop_dell_precision.2', {}),
    ('one/two/headphones_apple_pro.3', {}),
    ('one/two/three/headphones_apple_pro.4', {}),
    ('one/two/three/four/headphones_apple_pro.5', {})]))
def test_get_depth_error(repo: Repo) -> None:
    """
    Test that `onyo get --depth x` when a negative integer is used returns the
    expected exception
    """
    cmd = ['onyo', 'get', '--depth', '-1', '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    assert ret.stderr
    assert "-d, --depth must be 0 or larger, not '-1'" in ret.stderr
    assert ret.returncode == 1


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {}),
    ('one/laptop_dell_precision.2', {}),
    ('one/two/headphones_apple_pro.3', {}),
    ('one/two/three/headphones_apple_pro.4', {}),
    ('one/two/three/four/headphones_apple_pro.5', {}),
    ('another/dir/headphones_apple_pro.5', {})]))
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
def test_get_path_at_depth(
        repo: Repo, paths: str, depth: Union[str, None],
        expected: int) -> None:
    """
    Test that `onyo get --path x --depth y` retrieves the expected assets by
    ensuring that `depth` is assessed relative to the given paths.

    A portion of the parameters tests the usage of path with the default
    value of depth, when no depth is specified.
    """
    cmd = ['onyo', 'get', '-H']
    cmd += ['--path', *paths] if paths else []
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


@pytest.mark.repo_contents(*convert_contents([
    ('laptop_apple_macbookpro.1', {}),
    ('one/laptop_dell_precision.2', {}),
    ('one/two/headphones_apple_pro.3', {}),
    ('one/two/three/headphones_apple_pro.4', {}),
    ('one/two/three/four/headphones_apple_pro.5', {}),
    ('another/dir/headphones_apple_pro.5', {})]))
@pytest.mark.parametrize('path', [
    '/one/two/three',
    './path/that/does/not/exist/but/is/very/long',
    '/path/that/does/not/exist/and/does/not/start/with/dot',
    'path/that/does/not/exist/and/does/not/start/with/dot/slash',
    'def/ghi'])
def test_get_path_error(repo: Repo, path: str) -> None:
    """
    Test that `onyo get --path x --depth y` returns an exception if an invalid
    path is being used
    """
    cmd = ['onyo', 'get', '--path', path, '-H']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    eval_path = Path(path)
    assert f"cannot access '{str(eval_path)}': No such directory" in ret.stderr
    assert ret.returncode == 1


@pytest.mark.repo_contents(*convert_contents([
    ('a13bc_foo_bar.1', {'num': 'num-3'}),
    ('a2cd_foo_bar.2', {'num': 'num-16'}),
    ('a36ab_foo_bar.3', {'num': 'num-20'})]))
@pytest.mark.parametrize('sort,default', [
    ('-s', None), ('-S', None),
    (None, ['a2cd_foo_bar.2', 'a13bc_foo_bar.1', 'a36ab_foo_bar.3'])])
@pytest.mark.parametrize('keys,expected', [
    (['type'], ['a2cd', 'a13bc', 'a36ab']),
    (['num'], ['num-3', 'num-16', 'num-20']),
    (['unset', 'type'], ['a2cd', 'a13bc', 'a36ab']),
    ([], ['a2cd', 'a13bc', 'a36ab'])])
def test_get_sort(
        repo: Repo, sort: Union[str, None], keys: list[str],
        expected: list[str], default: Union[int, None]) -> None:
    """
    Test that `onyo get --keys x y z` with `-s` (ascending) or `-S`
    (descending)  retrieves assets in the expected 'natural sorted' order.
    """
    cmd = ['onyo', 'get', '-H']
    cmd += ['--keys', *keys] if keys else []
    cmd += [sort] if sort else []
    ret = subprocess.run(cmd, capture_output=True, text=True)
    output = [output.split('\t') for output in ret.stdout.split('\n')][:-1]

    for i, key in enumerate(keys or ['type']):
        if key == 'unset':  # nothing to be sorted
            continue

        assert [line[i if sort else -1] for line in output] == default if \
            default else list(reversed(expected)) if sort == '-S' else expected

    assert not ret.stderr
    assert ret.returncode == 0


def test_get_sort_error(repo: Repo) -> None:
    """
    Test that when using -s and -S simultaneously the appropriate error is
    returned.
    """
    cmd = ['onyo', 'get', '-s', '-S']
    ret = subprocess.run(cmd, capture_output=True, text=True)
    msg = (
        '--sort-ascending (-s) and --sort-descending (-S) cannot be used '
        'together')
    assert msg in ret.stderr
    assert ret.returncode == 1


@pytest.mark.parametrize('assets', [[
    (Path('a13bc_foo_bar.1'), {'num': 'num-20', 'str': 'abc', 'id': '1'}),
    (Path('a2cd_foo_bar.2'), {'num': 'num-3', 'str': 'def', 'id': '2'}),
    (Path('a36ab_foo_bar.3'), {'num': 'num-16', 'str': 'ghi', 'id': '3'})]])
@pytest.mark.parametrize('keys', [None, ['num'], ['str', 'num']])
@pytest.mark.parametrize('reverse', [True, False])
def test_natural_sort(
        assets: list[tuple[Path, dict[str, str]]], keys: Union[list, None],
        reverse: bool) -> None:
    """Test implementation of natural sorting algorithm"""
    sorted_assets = natural_sort(assets, keys=keys, reverse=reverse)
    ids = [data.get('id') for _, data in sorted_assets]

    if reverse:
        ids = list(reversed(ids))

    if keys is None:
        assert ids == ['2', '1', '3']
    elif keys[0] == 'num':
        assert ids == ['2', '3', '1']
    elif keys[0] == 'str':
        assert ids == ['1', '2', '3']


@pytest.mark.parametrize('assets', [[
    (Path('a13bc_foo_bar.1'), {'num': 'num-20', 'str': 'abc'}),
    (Path('a2cd_foo_bar.2'), {'num': 'num-3'}),
    (Path('a36ab_foo_bar.3'), {'str': 'ghi'})]])
@pytest.mark.parametrize('keys', [[
    'type', 'make', 'model', 'serial', 'num', 'str', 'id']])
def test_fill_unset(
        assets: list[tuple[Path, dict[str, str]]], keys: list[str]) -> None:
    """
    Test that the `fill_unset()` function fills unset keys with the value
    `'<unset>'`
    """
    unset_value = '<unset>'
    filled = list(fill_unset((a for a in assets), keys=keys))
    for i, (asset, data) in enumerate(filled):
        assert isinstance(asset, Path)
        assert asset == assets[i][0]
        for k, v in data.items():
            assert v == assets[i][1].get(k, unset_value)

    assert filled[1][1]['str'] == unset_value
    assert filled[2][1]['num'] == unset_value


@pytest.mark.parametrize('filters', [
    ['type=laptop'], ['type=laptop', 'make=foo', 'bar=1']])
def test_set_filters(repo: Repo, filters: list[str]) -> None:
    """
    Test that the `set_filters()` function creates Filter objects with
    the expected properties
    """
    validated_filters = set_filters(filters, repo=repo)
    filter_dict = {k: v for k, v in [f.split('=', 1) for f in filters]}
    for f in validated_filters:
        assert f.value == filter_dict[f.key]

    assert len(validated_filters) == len(filters)
    assert all(isinstance(f, Filter) for f in validated_filters)


@pytest.mark.parametrize(
    'filters,expected', [
        (['badfilter'], 'Filters must be formatted as `key=value`'),
        (['type=laptop', 'type=laptop'], 'Duplicate filter keys: ')])
@pytest.mark.parametrize('rich', [True, False])
def test_set_filters_error(
        capsys, repo: Repo, filters: list[str], expected: str,
        rich: bool) -> None:
    """
    Test that when invalid filters (i.e., not conforming to the `key=value`
    format) or duplicate filters are passed to `set_filters()` the
    appropriate error response is returned.
    """
    with pytest.raises(SystemExit) as exc:
        _ = set_filters(filters, repo=repo, rich=rich)

    captured = capsys.readouterr()
    assert expected in captured.err
    assert str(exc.value) == '1'


def test_sanitize_keys() -> None:
    """
    Test that the `sanitize_keys()` function removes duplicates and uses
    default keys when no keys are given.
    """
    defaults = ['foo', 'bar']
    assert sanitize_keys(['a', 'b'], defaults) == ['a', 'b']
    assert sanitize_keys(['a', 'a'], defaults) == ['a']
    assert sanitize_keys([], defaults) == ['foo', 'bar']
