import pytest

from itertools import product

from onyo.lib.exceptions import OnyoInvalidFilterError
from onyo.lib.filters import Filter
from onyo.lib.items import Item


class TestFilter:
    r"""Filter with literal text.

    Whether the ``Filter`` objects are initialized correctly, and the matching
    is correct.
    """

    def read_asset(self,
                   name: str) -> Item:
        r"""Get a populated Item."""

        item = Item(type='<to-set>',
                    make='make',
                    model='model',
                    serial='<to-set>')

        match name:
            case 'laptop_make_model.1':
                item.update({'type': 'laptop', 'serial': '1', 'key': 'value'})
            case 'monitor_make_model.2':
                item.update({'type': 'monitor', 'serial': '2', 'foo': 'bar'})
            case 'headphones_make_model.3':
                item.update({'type': 'headphones', 'serial': '3'})
            case 'wheelchair_make_model.4':
                item.update({'type': 'wheelchair', 'serial': '4', 'foo': None})
            case 'wheelchair_make_model.5':
                item.update({'type': 'wheelchair', 'serial': '5', 'foo': ''})
            case _:
                raise ValueError("Unknown asset")

        return item

    @pytest.mark.parametrize('filt', ['type=laptop', 'key=value', 'serial=2'])
    def test_filter_equal(self,
                          filt: str) -> None:
        """Literal text equals."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operator == '='
        assert f.value == filt.split('=', 1)[1]

        match filt.split('=', 1)[1]:
            case 'laptop':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case 'value':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type!=laptop', 'key!=value', 'serial!=2'])
    def test_filter_not_equal(self,
                              filt: str) -> None:
        """Literal text not equals."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operator == '!='
        assert f.value == filt.split('!=', 1)[1]

        match filt.split('=', 1)[1]:
            case 'laptop':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case 'value':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type>laptop', 'key>value', 'serial>2'])
    def test_filter_greater_than(self,
                                 filt: str) -> None:
        """Literal text greater than."""

        f = Filter(filt)
        assert f.key == filt.split('>', 1)[0]
        assert f.operator == '>'
        assert f.value == filt.split('>', 1)[1]
        assert not f.match(self.read_asset('laptop_make_model.1'))

        match filt.split('>', 1)[1]:
            case 'laptop':
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case 'value':
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type>=laptop', 'key>=value', 'serial>=2'])
    def test_filter_greater_than_or_equal(self,
                                          filt: str) -> None:
        """Literal text greater than or equal."""

        f = Filter(filt)
        assert f.key == filt.split('>=', 1)[0]
        assert f.operator == '>='
        assert f.value == filt.split('>=', 1)[1]

        match filt.split('>=', 1)[1]:
            case 'laptop':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case 'value':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type<laptop', 'key<value', 'serial<2'])
    def test_filter_less_than(self,
                              filt: str) -> None:
        """Literal text less than."""

        f = Filter(filt)
        assert f.key == filt.split('<', 1)[0]
        assert f.operator == '<'
        assert f.value == filt.split('<', 1)[1]

        match filt.split('<', 1)[1]:
            case 'laptop':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case 'value':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type<=laptop', 'key<=value', 'serial<=2'])
    def test_filter_less_than_or_equal(self,
                                       filt: str) -> None:
        """Literal text less than or equal."""

        f = Filter(filt)
        assert f.key == filt.split('<=', 1)[0]
        assert f.operator == '<='
        assert f.value == filt.split('<=', 1)[1]

        match filt.split('<=', 1)[1]:
            case 'laptop':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case 'value':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))


class TestFilterRegex:
    r"""Filter with regular expressions.

    Whether the ``Filter`` objects are initialized correctly, and the matching
    is correct.
    """

    def read_asset(self,
                   name: str) -> Item:
        r"""Get a populated Item."""

        item = Item(type='<to-set>',
                    make='make',
                    model='model',
                    serial='<to-set>')

        match name:
            case 'laptop_make_model.1':
                item.update({'type': 'laptop', 'serial': '1', 'key': 'value'})
            case 'monitor_make_model.2':
                item.update({'type': 'monitor', 'serial': '2', 'foo': 'bar'})
            case 'headphones_make_model.3':
                item.update({'type': 'headphones', 'serial': '3'})
            case 'wheelchair_make_model.4':
                item.update({'type': 'wheelchair', 'serial': '4', 'foo': None})
            case 'wheelchair_make_model.5':
                item.update({'type': 'wheelchair', 'serial': '5', 'foo': ''})
            case _:
                raise ValueError("Unknown asset")

        return item

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['type', 'missing'],
                                 ['='],
                                 ['.*', '.*no-match.*', '.*eel.*', '(?i)LAPTOP'],
                             )])
    def test_filter_regex_equal(self,
                                filt: str) -> None:
        """Regular expression equal."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operator == '='
        assert f.value == filt.split('=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('laptop_make_model.1'))
            assert not f.match(self.read_asset('monitor_make_model.2'))
            assert not f.match(self.read_asset('headphones_make_model.3'))
            assert not f.match(self.read_asset('wheelchair_make_model.4'))
            assert not f.match(self.read_asset('wheelchair_make_model.5'))
        else:
            match f.value:
                case '.*':
                    assert f.match(self.read_asset('laptop_make_model.1'))
                    assert f.match(self.read_asset('monitor_make_model.2'))
                    assert f.match(self.read_asset('headphones_make_model.3'))
                    assert f.match(self.read_asset('wheelchair_make_model.4'))
                    assert f.match(self.read_asset('wheelchair_make_model.5'))
                case '.*no-match.*':
                    assert not f.match(self.read_asset('laptop_make_model.1'))
                    assert not f.match(self.read_asset('monitor_make_model.2'))
                    assert not f.match(self.read_asset('headphones_make_model.3'))
                    assert not f.match(self.read_asset('wheelchair_make_model.4'))
                    assert not f.match(self.read_asset('wheelchair_make_model.5'))
                case '.*eel.*':
                    assert not f.match(self.read_asset('laptop_make_model.1'))
                    assert not f.match(self.read_asset('monitor_make_model.2'))
                    assert not f.match(self.read_asset('headphones_make_model.3'))
                    assert f.match(self.read_asset('wheelchair_make_model.4'))
                    assert f.match(self.read_asset('wheelchair_make_model.5'))
                case '(?i)LAPTOP':
                    assert f.match(self.read_asset('laptop_make_model.1'))
                    assert not f.match(self.read_asset('monitor_make_model.2'))
                    assert not f.match(self.read_asset('headphones_make_model.3'))
                    assert not f.match(self.read_asset('wheelchair_make_model.4'))
                    assert not f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['type', 'missing'],
                                 ['!='],
                                 ['.*', '.*no-match.*', '.*eel.*', '(?i)LAPTOP'],
                             )])
    def test_filter_regex_not_equal(self,
                                    filt: str) -> None:
        """Regular expression not equal."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operator == '!='
        assert f.value == filt.split('!=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('laptop_make_model.1'))
            assert not f.match(self.read_asset('monitor_make_model.2'))
            assert not f.match(self.read_asset('headphones_make_model.3'))
            assert not f.match(self.read_asset('wheelchair_make_model.4'))
            assert not f.match(self.read_asset('wheelchair_make_model.5'))
        else:
            match f.value:
                case '.*':
                    assert not f.match(self.read_asset('laptop_make_model.1'))
                    assert not f.match(self.read_asset('monitor_make_model.2'))
                    assert not f.match(self.read_asset('headphones_make_model.3'))
                    assert not f.match(self.read_asset('wheelchair_make_model.4'))
                    assert not f.match(self.read_asset('wheelchair_make_model.5'))
                case '.*no-match.*':
                    assert f.match(self.read_asset('laptop_make_model.1'))
                    assert f.match(self.read_asset('monitor_make_model.2'))
                    assert f.match(self.read_asset('headphones_make_model.3'))
                    assert f.match(self.read_asset('wheelchair_make_model.4'))
                    assert f.match(self.read_asset('wheelchair_make_model.5'))
                case '.*eel.*':
                    assert f.match(self.read_asset('laptop_make_model.1'))
                    assert f.match(self.read_asset('monitor_make_model.2'))
                    assert f.match(self.read_asset('headphones_make_model.3'))
                    assert not f.match(self.read_asset('wheelchair_make_model.4'))
                    assert not f.match(self.read_asset('wheelchair_make_model.5'))
                case '(?i)LAPTOP':
                    assert not f.match(self.read_asset('laptop_make_model.1'))
                    assert f.match(self.read_asset('monitor_make_model.2'))
                    assert f.match(self.read_asset('headphones_make_model.3'))
                    assert f.match(self.read_asset('wheelchair_make_model.4'))
                    assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['type', 'missing'],
                                 ['>', '>='],
                                 ['.*', '.*no-match.*', '.*eel.*', '(?i)LAPTOP'],
                             )])
    def test_filter_regex_greater_than(self,
                                       filt: str) -> None:
        """Regex greater than and greater than or equal.

        Regular expressions are weird when used with greater than and less than.

        If it were possible, it would be disallowed (like tags).

        ``>``, ``>=``, ``<``, and ``<=`` treat the regular expression as a
        literal string, but sort it using natsort's humansort, which can lead to
        surprising results.
        """

        f = Filter(filt)

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('laptop_make_model.1'))
            assert not f.match(self.read_asset('monitor_make_model.2'))
            assert not f.match(self.read_asset('headphones_make_model.3'))
            assert not f.match(self.read_asset('wheelchair_make_model.4'))
            assert not f.match(self.read_asset('wheelchair_make_model.5'))
        else:
            assert f.match(self.read_asset('laptop_make_model.1'))
            assert f.match(self.read_asset('monitor_make_model.2'))
            assert f.match(self.read_asset('headphones_make_model.3'))
            assert f.match(self.read_asset('wheelchair_make_model.4'))
            assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['type', 'missing'],
                                 ['<', '<='],
                                 ['.*', '.*no-match.*', '.*eel.*', '(?i)LAPTOP'],
                             )])
    def test_filter_regex_less_than(self,
                                    filt: str) -> None:
        """Regex less than and less than or equal.

        Regular expressions are weird when used with greater than and less than.

        If it were possible, it would be disallowed (like tags).

        ``>``, ``>=``, ``<``, and ``<=`` treat the regular expression as a
        literal string, but sort it using natsort's humansort, which can lead to
        surprising results.
        """

        f = Filter(filt)

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('laptop_make_model.1'))
            assert not f.match(self.read_asset('monitor_make_model.2'))
            assert not f.match(self.read_asset('headphones_make_model.3'))
            assert not f.match(self.read_asset('wheelchair_make_model.4'))
            assert not f.match(self.read_asset('wheelchair_make_model.5'))
        else:
            assert not f.match(self.read_asset('laptop_make_model.1'))
            assert not f.match(self.read_asset('monitor_make_model.2'))
            assert not f.match(self.read_asset('headphones_make_model.3'))
            assert not f.match(self.read_asset('wheelchair_make_model.4'))
            assert not f.match(self.read_asset('wheelchair_make_model.5'))


class TestFilterTags:
    r"""Filter with tags.

    Whether the ``Filter`` objects are initialized correctly, and the matching
    is correct.

    This includes type tags (e.g. ``<bool>``, ``<dict>``, ``<list>``), value
    tags (``<empty>``, ``<false>``, ``<null>``, ``<true>``), and ``<unset>``.
    """

    def read_asset(self,
                   name: str) -> Item:
        r"""Get a populated Item."""

        item = Item(type='<to-set>',
                    make='make',
                    model='model',
                    serial='<to-set>',
                    key='<to-set>')

        match name:
            case 'str_make_model.1':
                item.update({'type': 'str', 'serial': '1', 'key': 'value'})
            case 'str_make_model.2':
                item.update({'type': 'str', 'serial': '2', 'key': ''})
            case 'list_make_model.3':
                item.update({'type': 'list', 'serial': '3', 'key': ['a', 'b', 'c']})
            case 'list_make_model.4':
                item.update({'type': 'list', 'serial': '4', 'key': []})
            case 'dict_make_model.5':
                item.update({'type': 'dict', 'serial': '5', 'key': {'a': 'b', 'c': 'd'}})
            case 'dict_make_model.6':
                item.update({'type': 'dict', 'serial': '6', 'key': {}})
            case 'bool_make_model.7':
                item.update({'type': 'bool', 'serial': '7', 'key': True})
            case 'bool_make_model.8':
                item.update({'type': 'bool', 'serial': '8', 'key': False})
            case 'null_make_model.9':
                item.update({'type': 'null', 'serial': '9', 'key': None})
            case _:
                raise ValueError("Unknown asset")

        return item

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['='],
                                 ['<bool>', '<dict>', '<list>'],
                             )])
    def test_filter_tag_type_equal(self,
                                   filt: str) -> None:
        """Tag type equals."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operator == '='
        assert f.value == filt.split('=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '<bool>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '<dict>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '<list>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['!='],
                                 ['<bool>', '<dict>', '<list>'],
                             )])
    def test_filter_tag_type_not_equal(self,
                                       filt: str) -> None:
        """Tag type not equals."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operator == '!='
        assert f.value == filt.split('!=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '<bool>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case '<dict>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case '<list>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['>', '>=', '<', '<='],
                                 ['<bool>', '<dict>', '<list>'],
                             )])
    def test_filter_tag_type_gt_lt(self,
                                   filt: str) -> None:
        """Tag type greater/less than.

        Filtering tags is not supported using ``>``, ``>=``, ``<``, and ``<=``.
        """

        f = Filter(filt)

        # greater/less than comparison is not allowed for tags
        assert not f.match(self.read_asset('str_make_model.1'))
        assert not f.match(self.read_asset('str_make_model.2'))
        assert not f.match(self.read_asset('list_make_model.3'))
        assert not f.match(self.read_asset('list_make_model.4'))
        assert not f.match(self.read_asset('dict_make_model.5'))
        assert not f.match(self.read_asset('dict_make_model.6'))
        assert not f.match(self.read_asset('bool_make_model.7'))
        assert not f.match(self.read_asset('bool_make_model.8'))
        assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['='],
                                 ['<empty>', '<false>', '<null>', '<true>'],
                             )])
    def test_filter_tag_value_equal(self,
                                    filt: str) -> None:
        """Tag value equal."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operator == '='
        assert f.value == filt.split('=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '<empty>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case '<false>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '<null>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case '<true>':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['!='],
                                 ['<empty>', '<false>', '<null>', '<true>'],
                             )])
    def test_filter_tag_value_not_equal(self,
                                        filt: str) -> None:
        """Tag value not equal."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operator == '!='
        assert f.value == filt.split('!=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '<empty>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '<false>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case '<null>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '<true>':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['>', '>=', '<', '<='],
                                 ['<empty>', '<false>', '<null>', '<true>'],
                             )])
    def test_filter_tag_value_gt_lt(self,
                                   filt: str) -> None:
        """Tag value greater/less than.

        Filtering tags is not supported using ``>``, ``>=``, ``<``, and ``<=``.
        """

        f = Filter(filt)

        # greater/less than comparison is not allowed for tags
        assert not f.match(self.read_asset('str_make_model.1'))
        assert not f.match(self.read_asset('str_make_model.2'))
        assert not f.match(self.read_asset('list_make_model.3'))
        assert not f.match(self.read_asset('list_make_model.4'))
        assert not f.match(self.read_asset('dict_make_model.5'))
        assert not f.match(self.read_asset('dict_make_model.6'))
        assert not f.match(self.read_asset('bool_make_model.7'))
        assert not f.match(self.read_asset('bool_make_model.8'))
        assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['='],
                                 ['<unset>'],
                             )])
    def test_filter_tag_unset_equal(self,
                                    filt: str) -> None:
        """Tag ``<unset>`` equal."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operator == '='
        assert f.value == filt.split('=', 1)[1]

        match f.key:
            case 'key':
                assert not f.match(self.read_asset('str_make_model.1'))
                assert not f.match(self.read_asset('str_make_model.2'))
                assert not f.match(self.read_asset('list_make_model.3'))
                assert not f.match(self.read_asset('list_make_model.4'))
                assert not f.match(self.read_asset('dict_make_model.5'))
                assert not f.match(self.read_asset('dict_make_model.6'))
                assert not f.match(self.read_asset('bool_make_model.7'))
                assert not f.match(self.read_asset('bool_make_model.8'))
                assert not f.match(self.read_asset('null_make_model.9'))
            case 'missing':
                assert f.match(self.read_asset('str_make_model.1'))
                assert f.match(self.read_asset('str_make_model.2'))
                assert f.match(self.read_asset('list_make_model.3'))
                assert f.match(self.read_asset('list_make_model.4'))
                assert f.match(self.read_asset('dict_make_model.5'))
                assert f.match(self.read_asset('dict_make_model.6'))
                assert f.match(self.read_asset('bool_make_model.7'))
                assert f.match(self.read_asset('bool_make_model.8'))
                assert f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['!='],
                                 ['<unset>'],
                             )])
    def test_filter_tag_unset_not_equal(self,
                                        filt: str) -> None:
        """Tag ``<unset>`` not equal."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operator == '!='
        assert f.value == filt.split('!=', 1)[1]

        match f.key:
            case 'key':
                assert f.match(self.read_asset('str_make_model.1'))
                assert f.match(self.read_asset('str_make_model.2'))
                assert f.match(self.read_asset('list_make_model.3'))
                assert f.match(self.read_asset('list_make_model.4'))
                assert f.match(self.read_asset('dict_make_model.5'))
                assert f.match(self.read_asset('dict_make_model.6'))
                assert f.match(self.read_asset('bool_make_model.7'))
                assert f.match(self.read_asset('bool_make_model.8'))
                assert f.match(self.read_asset('null_make_model.9'))
            case 'missing':
                assert not f.match(self.read_asset('str_make_model.1'))
                assert not f.match(self.read_asset('str_make_model.2'))
                assert not f.match(self.read_asset('list_make_model.3'))
                assert not f.match(self.read_asset('list_make_model.4'))
                assert not f.match(self.read_asset('dict_make_model.5'))
                assert not f.match(self.read_asset('dict_make_model.6'))
                assert not f.match(self.read_asset('bool_make_model.7'))
                assert not f.match(self.read_asset('bool_make_model.8'))
                assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['>', '>=', '<', '<='],
                                 ['<unset>'],
                             )])
    def test_filter_tag_unset_gt_lt(self,
                                    filt: str) -> None:
        """Tag ``<unset>`` greater/less than.

        Filtering tags is not supported using ``>``, ``>=``, ``<``, and ``<=``.
        """

        f = Filter(filt)

        # greater/less than comparison is not allowed for tags
        assert not f.match(self.read_asset('str_make_model.1'))
        assert not f.match(self.read_asset('str_make_model.2'))
        assert not f.match(self.read_asset('list_make_model.3'))
        assert not f.match(self.read_asset('list_make_model.4'))
        assert not f.match(self.read_asset('dict_make_model.5'))
        assert not f.match(self.read_asset('dict_make_model.6'))
        assert not f.match(self.read_asset('bool_make_model.7'))
        assert not f.match(self.read_asset('bool_make_model.8'))
        assert not f.match(self.read_asset('null_make_model.9'))


class TestFilterLiterals:
    r"""Filter with empty literals.

    This includes ``[]``, ``{}``, ``''``, ``""``.

    Whether the ``Filter`` objects are initialized correctly, and the matching
    is correct.
    """

    def read_asset(self,
                   name: str) -> Item:
        r"""Get a populated Item."""

        item = Item(type='<to-set>',
                    make='make',
                    model='model',
                    serial='<to-set>',
                    key='<to-set>')

        match name:
            case 'str_make_model.1':
                item.update({'type': 'str', 'serial': '1', 'key': 'value'})
            case 'str_make_model.2':
                item.update({'type': 'str', 'serial': '2', 'key': ''})
            case 'list_make_model.3':
                item.update({'type': 'list', 'serial': '3', 'key': ['a', 'b', 'c']})
            case 'list_make_model.4':
                item.update({'type': 'list', 'serial': '4', 'key': []})
            case 'dict_make_model.5':
                item.update({'type': 'dict', 'serial': '5', 'key': {'a': 'b', 'c': 'd'}})
            case 'dict_make_model.6':
                item.update({'type': 'dict', 'serial': '6', 'key': {}})
            case 'bool_make_model.7':
                item.update({'type': 'bool', 'serial': '7', 'key': True})
            case 'bool_make_model.8':
                item.update({'type': 'bool', 'serial': '8', 'key': False})
            case 'null_make_model.9':
                item.update({'type': 'null', 'serial': '9', 'key': None})
            case _:
                raise ValueError("Unknown asset")

        return item

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['='],
                                 ['[]', '{}', "''", '""'],
                             )])
    def test_filter_literal_equal(self,
                                  filt: str) -> None:
        """Empty literal equal."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operator == '='
        assert f.value == filt.split('=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '[]':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '{}':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case "''" | '""':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['!='],
                                 ['[]', '{}', "''", '""'],
                             )])
    def test_filter_literal_not_equal(self,
                                      filt: str) -> None:
        """Empty literal not equal."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operator == '!='
        assert f.value == filt.split('!=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '[]':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case '{}':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))
                case "''" | '""':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert f.match(self.read_asset('bool_make_model.7'))
                    assert f.match(self.read_asset('bool_make_model.8'))
                    assert f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['>'],
                                 ['[]', '{}', "''", '""'],
                             )])
    def test_filter_literal_greater_than(self,
                                         filt: str) -> None:
        """Empty literal greater than."""

        f = Filter(filt)
        assert f.key == filt.split('>', 1)[0]
        assert f.operator == '>'
        assert f.value == filt.split('>', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '[]':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '{}':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case "''" | '""':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['>='],
                                 ['[]', '{}', "''", '""'],
                             )])
    def test_filter_literal_greater_than_or_equal(self,
                                                  filt: str) -> None:
        """Empty literal greater than or equal."""

        f = Filter(filt)
        assert f.key == filt.split('>=', 1)[0]
        assert f.operator == '>='
        assert f.value == filt.split('>=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '[]':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '{}':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case "''" | '""':
                    assert f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['<'],
                                 ['[]', '{}', "''", '""'],
                             )])
    def test_filter_literal_less_than(self,
                                      filt: str) -> None:
        """Empty literal less than."""

        f = Filter(filt)
        assert f.key == filt.split('<', 1)[0]
        assert f.operator == '<'
        assert f.value == filt.split('<', 1)[1]

        # nothing can be less than empty
        assert not f.match(self.read_asset('str_make_model.1'))
        assert not f.match(self.read_asset('str_make_model.2'))
        assert not f.match(self.read_asset('list_make_model.3'))
        assert not f.match(self.read_asset('list_make_model.4'))
        assert not f.match(self.read_asset('dict_make_model.5'))
        assert not f.match(self.read_asset('dict_make_model.6'))
        assert not f.match(self.read_asset('bool_make_model.7'))
        assert not f.match(self.read_asset('bool_make_model.8'))
        assert not f.match(self.read_asset('null_make_model.9'))

    @pytest.mark.parametrize('filt',
                             [''.join(x) for x in product(
                                 ['key', 'missing'],
                                 ['<='],
                                 ['[]', '{}', "''", '""'],
                             )])
    def test_filter_literal_less_than_or_equal(self,
                                               filt: str) -> None:
        """Empty literal less than or equal."""

        f = Filter(filt)
        assert f.key == filt.split('<=', 1)[0]
        assert f.operator == '<='
        assert f.value == filt.split('<=', 1)[1]

        if f.key == 'missing':
            # cannot match against an unset key
            assert not f.match(self.read_asset('str_make_model.1'))
            assert not f.match(self.read_asset('str_make_model.2'))
            assert not f.match(self.read_asset('list_make_model.3'))
            assert not f.match(self.read_asset('list_make_model.4'))
            assert not f.match(self.read_asset('dict_make_model.5'))
            assert not f.match(self.read_asset('dict_make_model.6'))
            assert not f.match(self.read_asset('bool_make_model.7'))
            assert not f.match(self.read_asset('bool_make_model.8'))
            assert not f.match(self.read_asset('null_make_model.9'))
        else:
            match f.value:
                case '[]':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case '{}':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert not f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))
                case "''" | '""':
                    assert not f.match(self.read_asset('str_make_model.1'))
                    assert f.match(self.read_asset('str_make_model.2'))
                    assert not f.match(self.read_asset('list_make_model.3'))
                    assert not f.match(self.read_asset('list_make_model.4'))
                    assert not f.match(self.read_asset('dict_make_model.5'))
                    assert not f.match(self.read_asset('dict_make_model.6'))
                    assert not f.match(self.read_asset('bool_make_model.7'))
                    assert not f.match(self.read_asset('bool_make_model.8'))
                    assert not f.match(self.read_asset('null_make_model.9'))


@pytest.mark.parametrize('filter_arg', [
    'key', 'key!value', '┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻',
    'key=', '=value', 'key!=', '!=value',
    'key>', '>value', 'key>=', '>=value',
    'key<', '<value', 'key<=', '<=value',
])
def test_filter_invalid(filter_arg: str) -> None:
    """Raise on invalid filter string."""

    with pytest.raises(OnyoInvalidFilterError) as exc:
        Filter(filter_arg)

    assert 'Filters must be formatted as `key=value`' in str(exc.value)


def test_filter_format() -> None:
    """Split filter string into ``key``, ``operator``, and ``value`` properties."""

    # =
    assert Filter._format('key=value') == ('key', '=', 'value')
    assert Filter._format('key=<unset>') == ('key', '=', '<unset>')
    assert Filter._format('key=value=value') == ('key', '=', 'value=value')

    # !=
    assert Filter._format('key!=value') == ('key', '!=', 'value')
    assert Filter._format('key!=<unset>') == ('key', '!=', '<unset>')
    assert Filter._format('key!=value=value') == ('key', '!=', 'value=value')

    # >
    assert Filter._format('key>value') == ('key', '>', 'value')
    assert Filter._format('key><unset>') == ('key', '>', '<unset>')
    assert Filter._format('key>value=value') == ('key', '>', 'value=value')

    # >=
    assert Filter._format('key>=value') == ('key', '>=', 'value')
    assert Filter._format('key>=<unset>') == ('key', '>=', '<unset>')
    assert Filter._format('key>=value=value') == ('key', '>=', 'value=value')

    # <
    assert Filter._format('key<value') == ('key', '<', 'value')
    assert Filter._format('key<<unset>') == ('key', '<', '<unset>')
    assert Filter._format('key<value=value') == ('key', '<', 'value=value')

    # <=
    assert Filter._format('key<=value') == ('key', '<=', 'value')
    assert Filter._format('key<=<unset>') == ('key', '<=', '<unset>')
    assert Filter._format('key<=value=value') == ('key', '<=', 'value=value')

    # pathological
    assert Filter._format('key<=<==>') == ('key', '<=', '<==>')
    assert Filter._format('key=>==<') == ('key', '=', '>==<')
    assert Filter._format('key!!=!==<') == ('key!', '!=', '!==<')
