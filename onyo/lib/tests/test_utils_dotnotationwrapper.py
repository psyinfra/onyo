import pytest
from onyo.lib.utils import DotNotationWrapper


def test_get_values():

    d = {'some': 'value',
         'nested': {'one': 1,
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
        dne = wrapper["dne"]  # noqa: F841
    assert exc_info.match("dne")
    with pytest.raises(TypeError) as exc_info:
        dne = wrapper['some.dne']  # noqa: F841
    assert exc_info.match("'some' is not a dictionary.")
    with pytest.raises(KeyError) as exc_info:
        dne = wrapper['nested.dne']  # noqa: F841
    assert exc_info.match("nested.dne")
    with pytest.raises(TypeError) as exc_info:
        dne = wrapper['nested.one.dne']  # noqa: F841
    assert exc_info.match("'nested.one' is not a dictionary.")
    with pytest.raises(KeyError) as exc_info:
        dne = wrapper['nested.deep.dne']  # noqa: F841
    assert exc_info.match("nested.deep.dne")
    with pytest.raises(TypeError) as exc_info:
        dne = wrapper['nested.deep.key.dne']  # noqa: F841
    assert exc_info.match("'nested.deep.key' is not a dictionary.")


def test_set_values():

    d = {'some': 'value',
         'nested': {'one': 1,
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

    # update from regular dict
    updater = {'regular': 'dict', 'some': 'different'}
    wrapper.update(updater)
    assert wrapper['regular'] == 'dict'
    assert wrapper['some'] == 'different'

    # update from another wrapped dict should allow for "recursive update":
    updater = {'nested': {'one': 3}}
    wrapper.update(DotNotationWrapper(updater))
    assert wrapper['nested.one'] == updater['nested']['one']
    assert wrapper['nested.two'] == '2'


def test_magic_methods():

    d = {'some': 'value',
         'nested': {'one': 1,
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

    # .values()
    values = [v for v in wrapper.values()]
    assert len(keys) == len(values)
    assert all(wrapper[k] in values for k in keys)
    assert all(v in [wrapper[k] for k in keys] for v in values)

    # .items()
    assert all(k in keys and v in values for k, v in wrapper.items())
    assert all(t in zip(keys, values) for t in wrapper.items())

    # len
    assert len(wrapper) == len(keys)

    # del
    del wrapper['nested.one']
    assert wrapper['nested.two'] == '2'
    with pytest.raises(KeyError):
        dne = wrapper['nested.one']  # noqa: F841

    # TODO: What about various ways of copying?