
import pytest

import wn


@pytest.mark.usefixtures('empty_db')
def test_lexicons_empty():
    assert len(wn.lexicons()) == 0


@pytest.mark.usefixtures('mini_db')
def test_lexicons_mini():
    assert len(wn.lexicons()) == 2
    assert all(isinstance(lex, wn.Lexicon) for lex in wn.lexicons())

    results = wn.lexicons(lgcode='en')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lgcode='es')
    assert len(results) == 1 and results[0].language == 'es'
    # results = wn.lexicons(lgcode='pt')
    # assert len(results) == 0

    results = wn.lexicons(lexicon='*')
    assert len(results) == 2
    results = wn.lexicons(lexicon='test-en')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lexicon='test-en:1')
    assert len(results) == 1 and results[0].language == 'en'
    results = wn.lexicons(lexicon='test-en:*')
    assert len(results) == 1 and results[0].language == 'en'
    # results = wn.lexicons(lexicon='test-pt')
    # assert len(results) == 0

