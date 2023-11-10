import pytest

from onyo.lib import Filter, OnyoInvalidFilterError


@pytest.mark.parametrize('filt', ['type=laptop', 'key=value', 'foo=<unset>'])
def test_filter(filt: str) -> None:
    """
    Test whether instances of the Filter object are set up properly, including
    post-initialization behavior
    """

    def read_asset(name: str) -> dict:
        if name == 'laptop_make_model.1':
            return dict(type='laptop',
                        make='make',
                        model='model',
                        serial='1',
                        key='value')
        elif name == 'monitor_make_model.2':
            return dict(type='monitor',
                        make='make',
                        model='model',
                        serial='2',
                        foo='bar')
        elif name == 'headphones_make_model.3':
            return dict(type='headphones',
                        make='make',
                        model='model',
                        serial='3')
        elif name == 'wheelchair_make_model.4':
            return dict(type='wheelchair',
                        make='make',
                        model='model',
                        serial='4',
                        foo=None)
        elif name == 'wheelchair_make_model.5':
            return dict(type='wheelchair',
                        make='make',
                        model='model',
                        serial='5',
                        foo='')
        else:
            raise ValueError("Unknown asset")

    f = Filter(filt)
    assert f.key == filt.split('=', 1)[0]
    assert f.value == filt.split('=', 1)[1]
    assert f.match(read_asset('laptop_make_model.1'))
    assert not f.match(read_asset('monitor_make_model.2'))

    if filt.split('=', 1)[1] == '<unset>':
        assert f.match(read_asset('headphones_make_model.3'))
        assert f.match(read_asset('wheelchair_make_model.4'))
        assert f.match(read_asset('wheelchair_make_model.5'))
    else:
        assert not f.match(read_asset('headphones_make_model.3'))
        assert not f.match(read_asset('wheelchair_make_model.4'))
        assert not f.match(read_asset('wheelchair_make_model.5'))


@pytest.mark.parametrize('filt', ['key=<list>', 'key=<dict>'])
def test_filter_match_type(filt: str) -> None:
    """
    Test filtering by string type (e.g., <list> or <dict>)
    """
    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        elif name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key={'a': 'b', 'c': 'd'})

    string_type = filt.split('=', 1)[1]
    f = Filter(filt)
    if string_type == '<list>':
        assert f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
    elif string_type == '<dict>':
        assert not f.match(read_asset('type_make_model.1'))
        assert f.match(read_asset('type_make_model.2'))


def test_filter_re_match() -> None:
    """Test filtering by regular expression"""
    assert not Filter._re_match(text='foo(', r='foo(')
    assert Filter._re_match(text='foo', r='foo')
    assert Filter._re_match(text='foobar', r='foo.*')


@pytest.mark.parametrize('filter_arg', [
    'key', 'key!value', '┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻'])
def test_filter_invalid(filter_arg: str) -> None:
    """Test whether invalid filters raise the expected exception"""

    with pytest.raises(OnyoInvalidFilterError) as exc:
        Filter('key')

    assert 'Filters must be formatted as `key=value`' in str(exc.value)


def test_filter_format() -> None:
    """Test whether the input argument 'key=value' is properly formatted into
    the `key` and `value` properties"""
    assert Filter._format('key=value') == ['key', 'value']
    assert Filter._format('key=value=value') == ['key', 'value=value']
