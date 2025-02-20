import pytest

from onyo.lib.exceptions import OnyoInvalidFilterError
from onyo.lib.filters import Filter
from onyo.lib.items import Item


class TestFilter:

    def read_asset(self,
                   name: str) -> Item:
        r"""
        """

        if name == 'laptop_make_model.1':
            return Item(type='laptop',
                        make='make',
                        model='model',
                        serial='1',
                        key='value')
        elif name == 'monitor_make_model.2':
            return Item(type='monitor',
                        make='make',
                        model='model',
                        serial='2',
                        foo='bar')
        elif name == 'headphones_make_model.3':
            return Item(type='headphones',
                        make='make',
                        model='model',
                        serial='3')
        elif name == 'wheelchair_make_model.4':
            return Item(type='wheelchair',
                        make='make',
                        model='model',
                        serial='4',
                        foo=None)
        elif name == 'wheelchair_make_model.5':
            return Item(type='wheelchair',
                        make='make',
                        model='model',
                        serial='5',
                        foo='')
        else:
            raise ValueError("Unknown asset")

    @pytest.mark.parametrize('filt', ['type=laptop', 'key=value', 'foo=<unset>', 'serial=2'])
    def test_filter_equal(self,
                          filt: str) -> None:
        """Test whether ``Filter`` object are set up, including post-initialization."""

        f = Filter(filt)
        assert f.key == filt.split('=', 1)[0]
        assert f.operand == '='
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
            case '<unset>':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type!=laptop', 'key!=value', 'foo!=<unset>', 'serial!=2'])
    def test_filter_not_equal(self,
                              filt: str) -> None:
        """Test whether ``Filter`` object are set up, including post-initialization."""

        f = Filter(filt)
        assert f.key == filt.split('!=', 1)[0]
        assert f.operand == '!='
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
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case '<unset>':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type>laptop', 'key>value', 'foo><unset>', 'serial>2'])
    def test_filter_greater_than(self,
                                 filt: str) -> None:
        """Test whether ``Filter`` object are set up, including post-initialization."""

        f = Filter(filt)
        assert f.key == filt.split('>', 1)[0]
        assert f.operand == '>'
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
            case '<unset>':
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type>=laptop', 'key>=value', 'foo>=<unset>', 'serial>=2'])
    def test_filter_greater_than_or_equal(self,
                                          filt: str) -> None:
        """Test whether ``Filter`` object are set up, including post-initialization."""

        f = Filter(filt)
        assert f.key == filt.split('>=', 1)[0]
        assert f.operand == '>='
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
            case '<unset>':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert not f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))

    @pytest.mark.parametrize('filt', ['type<laptop', 'key<value', 'foo<<unset>', 'serial<2'])
    def test_filter_less_than(self,
                              filt: str) -> None:
        """Test whether ``Filter`` object are set up, including post-initialization."""

        f = Filter(filt)
        assert f.key == filt.split('<', 1)[0]
        assert f.operand == '<'
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
            case '<unset>':
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

    @pytest.mark.parametrize('filt', ['type<=laptop', 'key<=value', 'foo<=<unset>', 'serial<=2'])
    def test_filter_less_than_or_equal(self,
                                       filt: str) -> None:
        """Test whether ``Filter`` object are set up, including post-initialization."""

        f = Filter(filt)
        assert f.key == filt.split('<=', 1)[0]
        assert f.operand == '<='
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
            case '<unset>':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert not f.match(self.read_asset('monitor_make_model.2'))
                assert f.match(self.read_asset('headphones_make_model.3'))
                assert f.match(self.read_asset('wheelchair_make_model.4'))
                assert f.match(self.read_asset('wheelchair_make_model.5'))
            case '2':
                assert f.match(self.read_asset('laptop_make_model.1'))
                assert f.match(self.read_asset('monitor_make_model.2'))
                assert not f.match(self.read_asset('headphones_make_model.3'))
                assert not f.match(self.read_asset('wheelchair_make_model.4'))
                assert not f.match(self.read_asset('wheelchair_make_model.5'))

@pytest.mark.parametrize('filt', ['key=<list>', 'key=<dict>'])
def test_filter_type_equal(filt: str) -> None:
    """Filtering by variable type (e.g., <list> or <dict>)."""

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


@pytest.mark.parametrize('filt', ['key><list>', 'key><dict>'])
def test_filter_type_greater_than(filt: str) -> None:
    """Filtering by variable type (e.g., <list> or <dict>)."""

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

    string_type = filt.split('>', 1)[1]
    f = Filter(filt)
    if string_type == '<list>':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
    elif string_type == '<dict>':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))


@pytest.mark.parametrize('filt', ['key>=<list>', 'key>=<dict>'])
def test_filter_type_greater_than_or_equal(filt: str) -> None:
    """Filtering by variable type (e.g., <list> or <dict>)."""

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

    string_type = filt.split('>=', 1)[1]
    f = Filter(filt)
    if string_type == '<list>':
        assert f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
    elif string_type == '<dict>':
        assert not f.match(read_asset('type_make_model.1'))
        assert f.match(read_asset('type_make_model.2'))


@pytest.mark.parametrize('filt', ['key<<list>', 'key<<dict>'])
def test_filter_type_less_than(filt: str) -> None:
    """Filtering by variable type (e.g., <list> or <dict>)."""

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

    string_type = filt.split('<', 1)[1]
    f = Filter(filt)
    if string_type == '<list>':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
    elif string_type == '<dict>':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))


@pytest.mark.parametrize('filt', ['key<=<list>', 'key<=<dict>'])
def test_filter_type_less_than_or_equal(filt: str) -> None:
    """Filtering by variable type (e.g., <list> or <dict>)."""

    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        if name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key=[])
        elif name == 'type_make_model.3':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='3',
                        key={'a': 'b', 'c': 'd'})
        elif name == 'type_make_model.4':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='4',
                        key={})

    string_type = filt.split('<=', 1)[1]
    f = Filter(filt)
    if string_type == '<list>':
        assert f.match(read_asset('type_make_model.1'))
        assert f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))
    elif string_type == '<dict>':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert f.match(read_asset('type_make_model.3'))
        assert f.match(read_asset('type_make_model.4'))


@pytest.mark.parametrize('filt', ['key=[]', 'key={}'])
def test_filter_empty_literal_equal(filt: str) -> None:
    """Filtering by variable type (e.g., <list> or <dict>)."""

    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        if name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key=[])
        elif name == 'type_make_model.3':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='3',
                        key={'a': 'b', 'c': 'd'})
        elif name == 'type_make_model.4':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='4',
                        key={})

    string_type = filt.split('=', 1)[1]
    f = Filter(filt)
    if string_type == '[]':
        assert not f.match(read_asset('type_make_model.1'))
        assert f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))
    elif string_type == '{}':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert f.match(read_asset('type_make_model.4'))


@pytest.mark.parametrize('filt', ['key>[]', 'key>{}'])
def test_filter_empty_literal_greater_than(filt: str) -> None:
    """Compare against a literal empty value (e.g., [] or {})."""

    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        if name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key=[])
        elif name == 'type_make_model.3':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='3',
                        key={'a': 'b', 'c': 'd'})
        elif name == 'type_make_model.4':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='4',
                        key={})

    string_type = filt.split('>', 1)[1]
    f = Filter(filt)
    if string_type == '[]':
        assert f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))
    elif string_type == '{}':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))


@pytest.mark.parametrize('filt', ['key>=[]', 'key>={}'])
def test_filter_empty_literal_greater_than_or_equal(filt: str) -> None:
    """Compare against a literal empty value (e.g., [] or {})."""

    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        if name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key=[])
        elif name == 'type_make_model.3':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='3',
                        key={'a': 'b', 'c': 'd'})
        elif name == 'type_make_model.4':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='4',
                        key={})

    string_type = filt.split('>=', 1)[1]
    f = Filter(filt)
    if string_type == '[]':
        assert f.match(read_asset('type_make_model.1'))
        assert f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))
    elif string_type == '{}':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert f.match(read_asset('type_make_model.3'))
        assert f.match(read_asset('type_make_model.4'))


@pytest.mark.parametrize('filt', ['key<[]', 'key<{}'])
def test_filter_empty_literal_less_than(filt: str) -> None:
    """Compare against a literal empty value (e.g., [] or {})."""

    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        if name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key=[])
        elif name == 'type_make_model.3':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='3',
                        key={'a': 'b', 'c': 'd'})
        elif name == 'type_make_model.4':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='4',
                        key={})

    string_type = filt.split('<', 1)[1]
    f = Filter(filt)
    if string_type == '[]':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))
    elif string_type == '{}':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))


@pytest.mark.parametrize('filt', ['key<=[]', 'key<={}'])
def test_filter_empty_literal_less_than_or_equal(filt: str) -> None:
    """Compare against a literal empty value (e.g., [] or {})."""

    def read_asset(name: str):
        if name == 'type_make_model.1':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='1',
                        key=['a', 'b', 'c'])
        if name == 'type_make_model.2':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='2',
                        key=[])
        elif name == 'type_make_model.3':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='3',
                        key={'a': 'b', 'c': 'd'})
        elif name == 'type_make_model.4':
            return dict(type='type',
                        make='make',
                        model='model',
                        serial='4',
                        key={})

    string_type = filt.split('<=', 1)[1]
    f = Filter(filt)
    if string_type == '[]':
        assert not f.match(read_asset('type_make_model.1'))
        assert f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert not f.match(read_asset('type_make_model.4'))
    elif string_type == '{}':
        assert not f.match(read_asset('type_make_model.1'))
        assert not f.match(read_asset('type_make_model.2'))
        assert not f.match(read_asset('type_make_model.3'))
        assert f.match(read_asset('type_make_model.4'))


def test_filter_re_equal() -> None:
    """Filtering with regular expressions."""

    assert not Filter._re_match(text='foo(', r='foo(')
    assert Filter._re_match(text='foo', r='foo')
    assert Filter._re_match(text='foobar', r='foo.*')


@pytest.mark.parametrize('filter_arg', [
    'key', 'key!value', '┻━┻ ︵ヽ(`Д´)ﾉ︵ ┻━┻',
    'key=', '=value', 'key!=', '!=value',
    'key>', '>value', 'key>=', '>=value',
    'key<', '<value', 'key<=', '<=value',
])
def test_filter_invalid(filter_arg: str) -> None:
    """Invalid filters raise the correct exception."""

    with pytest.raises(OnyoInvalidFilterError) as exc:
        Filter(filter_arg)

    assert 'Filters must be formatted as `key=value`' in str(exc.value)


def test_filter_format() -> None:
    """The input argument 'key=value' is formatted into ``key`` and ``value`` properties."""

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
