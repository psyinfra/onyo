import pytest
from onyo.lib.utils import DotNotationWrapper


def test_getshit():

    d = {'some': 'value',
         'nested': {
             'one': 1,
             'two': '2',
             'deep': {'key': 'value'}
                    }
         }

    wrapper = DotNotationWrapper(d)
    assert wrapper['some'] == d['some']
    assert wrapper['nested'] == d['nested']  # TODO: check dict-equal-helper
    assert wrapper['nested.one'] == d['nested']['one']
    assert wrapper['nested.deep'] == d['nested']['deep']
    assert wrapper['nested.deep.key'] == d['nested']['deep']['key']
    with pytest.raises(KeyError) as exc_info:
        dne = wrapper["nope"]
    assert exc_info.match("nope")
    with pytest.raises(TypeError) as exc_info:
        dne = wrapper['some.nope']
    assert exc_info.match("'some' is not a dictionary.")
    with pytest.raises(KeyError) as exc_info:
        dne = wrapper['nested.nope']
    assert exc_info.match("nested.nope")
    with pytest.raises(TypeError) as exc_info:
        dne = wrapper['nested.one.more']
    assert exc_info.match("'nested.one' is not a dictionary.")
    with pytest.raises(KeyError) as exc_info:
        dne = wrapper['nested.deep.dne']
    assert exc_info.match("nested.deep.dne")
    with pytest.raises(TypeError) as exc_info:
        dne = wrapper['nested.deep.key.invalid']
    assert exc_info.match("'nested.deep.key' is not a dictionary.")

    # TODO: Turn above TypeErrors in `KeyError(full-key) from TypeError(as above) from TypeError(str indices, etc ...)`


def test_setshit():

    d = {'some': 'value',
         'nested': {
             'one': 1,
             'two': '2',
             'deep': {'key': 'value'}
                    }
         }

    wrapper = DotNotationWrapper(d)
    wrapper['some'] = 'newvalue'
    assert wrapper.get('some') == 'newvalue'
    assert d['some'] == 'newvalue'

    wrapper['nested.deep.key'] = 1
    assert wrapper.get('nested.deep.key') == 1
    assert d['nested']['deep']['key'] == 1

    wrapper['nested.deep.newkey'] = 2
    assert wrapper.get('nested.deep.newkey') == 2
    assert d['nested']['deep']['newkey'] == 2

    # TODO: update()


def test_magic():

    d = {'some': 'value',
         'nested': {
             'one': 1,
             'two': '2',
             'deep': {'key': 'value'}
                    }
         }
    dot_keys = ['some', 'nested.one', 'nested.two', 'nested.deep.key']

    wrapper = DotNotationWrapper(d)
    # .keys()
    keys = [k for k in wrapper.keys()]
    assert all(k in keys for k in dot_keys)
    assert all(k in dot_keys for k in keys)

    # in
    assert all(k in wrapper for k in dot_keys)
    assert all(k in dot_keys for k in wrapper)


# What of these do we actually need now?
# Would any of that be a problem later?
# What about **dict? How does it work? items()?
# __delitem__
# __len__
# __iter__
# __copy__
# copy()
# values()
# items()
