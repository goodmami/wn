
import pytest

import wn
from wn.constants import (NOUN, VERB, ADJ, ADV)
from wn.util import synset_id_formatter
import wn.ic


def synsets(w: wn.Wordnet):
    return {
        'information': w.synset('test-en-0001-n'),
        'illustration_example': w.synset('test-en-0002-n'),
        'sample': w.synset('test-en-0004-n'),
        'random_sample': w.synset('test-en-0005-n'),
        'random_sample2': w.synset('test-en-0008-n'),  # no hypernyms
        'datum': w.synset('test-en-0006-n'),
        'illustrate_exemplify': w.synset('test-en-0003-v'),
        'resignate': w.synset('test-en-0007-v'),
    }


words = [
    'For', 'example', ':', 'random sample', '.',
    'This', 'will', 'illustrate', 'and', 'exemplify', '.',
    'A', 'sample', 'of', 'data', '.',
]


@pytest.mark.usefixtures('mini_db')
def test_compute_nodistribute_nosmoothing():
    w = wn.Wordnet('test-en:1')
    ss = synsets(w)
    assert wn.ic.compute(words, w, distribute_weight=False, smoothing=0) == {
        NOUN: {
            ss['information']: 4.0,
            ss['illustration_example']: 3.0,
            ss['sample']: 2.0,
            ss['random_sample']: 1.0,
            ss['random_sample2']: 1.0,
            ss['datum']: 1.0,
            None: 5.0,
        },
        VERB: {
            ss['illustrate_exemplify']: 2.0,
            ss['resignate']: 0.0,
            None: 2.0,
        },
        ADJ: {None: 0.0},
        ADV: {None: 0.0},
    }


@pytest.mark.usefixtures('mini_db')
def test_compute_nodistribute_smoothing():
    w = wn.Wordnet('test-en:1')
    ss = synsets(w)
    assert wn.ic.compute(words, w, distribute_weight=False, smoothing=1.0) == {
        NOUN: {
            ss['information']: 5.0,
            ss['illustration_example']: 4.0,
            ss['sample']: 3.0,
            ss['random_sample']: 2.0,
            ss['random_sample2']: 2.0,
            ss['datum']: 2.0,
            None: 6.0,
        },
        VERB: {
            ss['illustrate_exemplify']: 3.0,
            ss['resignate']: 1.0,
            None: 3.0,
        },
        ADJ: {None: 1.0},
        ADV: {None: 1.0},
    }


@pytest.mark.usefixtures('mini_db')
def test_compute_distribute_smoothing():
    w = wn.Wordnet('test-en:1')
    ss = synsets(w)
    assert wn.ic.compute(words, w, distribute_weight=True, smoothing=1.0) == {
        NOUN: {
            ss['information']: 4.5,
            ss['illustration_example']: 3.5,
            ss['sample']: 2.5,
            ss['random_sample']: 1.5,
            ss['random_sample2']: 1.5,
            ss['datum']: 2.0,
            None: 5.0,
        },
        VERB: {
            ss['illustrate_exemplify']: 3.0,
            ss['resignate']: 1.0,
            None: 3.0,
        },
        ADJ: {None: 1.0},
        ADV: {None: 1.0},
    }


@pytest.mark.usefixtures('mini_db')
def test_load(tmp_path):
    w = wn.Wordnet('test-en:1')
    icpath = tmp_path / 'foo.dat'
    icpath.write_text(
        'wnver:1234567890AbCdEf\n'
        '1n 4.0 ROOT\n'
        '2n 3.0\n'
        '4n 2.0\n'
        '5n 1.0\n'
        '8n 1.0 ROOT\n'
        '6n 1.0\n'
        '3v 2.0 ROOT\n'
        '7v 0.0 ROOT\n'
    )

    get_synset_id = synset_id_formatter('test-en-{offset:04}-{pos}')
    assert (wn.ic.load(icpath, w, get_synset_id=get_synset_id)
            == wn.ic.compute(words, w, distribute_weight=False, smoothing=0.0))
