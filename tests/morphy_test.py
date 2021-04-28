
import pytest

import wn
from wn.morphy import Morphy


@pytest.mark.usefixtures('mini_db')
def test_morphy():
    w = wn.Wordnet('test-en:1', lemmatizer=Morphy)
    m = w.lemmatizer
    assert list(m('examples', 'n')) == ['example']
    assert list(m('examples', 'v')) == []
    assert list(m('exemplifying', 'n')) == []
    assert list(m('exemplifying', 'v')) == ['exemplify']
    assert list(m('data', 'n')) == ['datum']
    assert list(m('datums', 'n')) == ['datum']  # expected false positive
