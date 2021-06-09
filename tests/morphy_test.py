
import pytest

import wn
from wn import morphy


def test_morphy_uninitialized():
    # An unintialized Morphy isn't very bright, but it starts up
    # fast. It relies on the database to filter bad items.
    m = morphy.Morphy()
    assert m('example', 'n') == {'n': {'example'}}
    assert m('examples', 'n') == {'n': {'examples', 'example'}}
    assert m('examples', 'v') == {'v': {'examples', 'example', 'exampl'}}
    assert m('exemplifying', 'n') == {'n': {'exemplifying'}}
    assert m('exemplifying', 'v') == {'v': {'exemplifying', 'exemplify', 'exemplifye'}}
    assert m('data', 'n') == {'n': {'data'}}
    assert m('datums', 'n') == {'n': {'datums', 'datum'}}  # expected false positive
    assert m('examples', None) == {None: {'examples'},
                                   'n': {'example'},
                                   'v': {'example', 'exampl'}}
    assert m('exemplifying', None) == {None: {'exemplifying'},
                                       'v': {'exemplify', 'exemplifye'}}
    assert m('data', None) == {None: {'data'}}


@pytest.mark.usefixtures('mini_db')
def test_morphy_initialized():
    w = wn.Wordnet('test-en:1')
    m = morphy.Morphy(wordnet=w)
    assert m('example', 'n') == {'n': {'example'}}
    assert m('examples', 'n') == {'n': {'example'}}
    assert m('examples', 'v') == {}
    assert m('exemplifying', 'n') == {}
    assert m('exemplifying', 'v') == {'v': {'exemplify'}}
    assert m('data', 'n') == {'n': {'datum'}}
    assert m('datums', 'n') == {'n': {'datum'}}  # expected false positive
    assert m('examples', None) == {'n': {'example'}}
    assert m('exemplifying', None) == {'v': {'exemplify'}}
    assert m('data', None) == {'n': {'datum'}}
