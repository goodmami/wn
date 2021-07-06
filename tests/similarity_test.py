
from math import log

import pytest

import wn
from wn import similarity as sim
from wn.taxonomy import taxonomy_depth
from wn.ic import information_content as infocont


def get_synsets(w):
    return {
        'information': w.synset('test-en-0001-n'),
        'example': w.synset('test-en-0002-n'),
        'sample': w.synset('test-en-0004-n'),
        'random sample': w.synset('test-en-0005-n'),
        'random sample2': w.synset('test-en-0008-n'),
        'datum': w.synset('test-en-0006-n'),
        'exemplify': w.synset('test-en-0003-v'),
    }


# some fake information content; computed using:
#   words = ['example', 'example', 'sample', 'random sample', 'illustrate']
#   ic = compute(words, wn.Wordnet('test-en'), distribute_weight=False)

ic = {
    'n': {'test-en-0001-n': 5.0,  # information
          'test-en-0002-n': 5.0,  # example, illustration
          'test-en-0004-n': 3.0,  # sample
          'test-en-0005-n': 2.0,  # random sample
          'test-en-0008-n': 2.0,  # random sample 2
          'test-en-0006-n': 1.0,  # datum
          None: 6.0},
    'v': {'test-en-0003-v': 2.0,  # exemplify, illustrate
          'test-en-0007-v': 1.0,  # resignate
          None: 2.0},
    'a': {None: 1.0},
    'r': {None: 1.0}
}


@pytest.mark.usefixtures('mini_db')
def test_path():
    ss = get_synsets(wn.Wordnet('test-en'))
    assert sim.path(ss['information'], ss['information']) == 1/1
    assert sim.path(ss['information'], ss['example']) == 1/2
    assert sim.path(ss['information'], ss['sample']) == 1/3
    assert sim.path(ss['information'], ss['random sample']) == 1/4
    assert sim.path(ss['random sample'], ss['datum']) == 1/5
    assert sim.path(ss['random sample2'], ss['datum']) == 0
    assert sim.path(ss['random sample2'], ss['datum'], simulate_root=True) == 1/4
    assert sim.path(ss['random sample'], ss['random sample2'], simulate_root=True) == 1/6
    with pytest.raises(wn.Error):
        sim.path(ss['example'], ss['exemplify'])
    with pytest.raises(wn.Error):
        sim.wup(ss['example'], ss['exemplify'], simulate_root=True)


@pytest.mark.usefixtures('mini_db')
def test_wup():
    ss = get_synsets(wn.Wordnet('test-en'))
    assert sim.wup(ss['information'], ss['information']) == (2*1) / (0+0+2*1)
    assert sim.wup(ss['information'], ss['example']) == (2*1) / (0+1+2*1)
    assert sim.wup(ss['information'], ss['sample']) == (2*1) / (0+2+2*1)
    assert sim.wup(ss['information'], ss['random sample']) == (2*1) / (0+3+2*1)
    assert sim.wup(ss['random sample'], ss['datum']) == (2*1) / (3+1+2*1)
    with pytest.raises(wn.Error):
        assert sim.wup(ss['random sample2'], ss['datum'])
    assert (sim.wup(ss['random sample2'], ss['datum'], simulate_root=True)
            == (2*1) / (1+2+2*1))
    assert (sim.wup(ss['random sample'], ss['random sample2'], simulate_root=True)
            == (2*1) / (4+1+2*1))
    with pytest.raises(wn.Error):
        sim.wup(ss['example'], ss['exemplify'])
    with pytest.raises(wn.Error):
        sim.wup(ss['example'], ss['exemplify'], simulate_root=True)


@pytest.mark.usefixtures('mini_db')
def test_lch():
    w = wn.Wordnet('test-en')
    ss = get_synsets(w)
    d_n = taxonomy_depth(w, 'n')
    assert sim.lch(ss['information'], ss['information'], d_n) == -log((0+1) / (2*d_n))
    assert sim.lch(ss['information'], ss['example'], d_n) == -log((1+1) / (2*d_n))
    assert sim.lch(ss['information'], ss['sample'], d_n) == -log((2+1) / (2*d_n))
    assert sim.lch(ss['information'], ss['random sample'], d_n) == -log((3+1) / (2*d_n))
    assert sim.lch(ss['random sample'], ss['datum'], d_n) == -log((4+1) / (2*d_n))
    with pytest.raises(wn.Error):
        assert sim.lch(ss['random sample2'], ss['datum'], d_n)
    assert (sim.lch(ss['random sample2'], ss['datum'], d_n, simulate_root=True)
            == -log((3+1) / (2*d_n)))
    assert (sim.lch(ss['random sample'], ss['random sample2'], d_n, simulate_root=True)
            == -log((5+1) / (2*d_n)))
    with pytest.raises(wn.Error):
        sim.lch(ss['example'], ss['exemplify'], d_n)
    with pytest.raises(wn.Error):
        sim.lch(ss['example'], ss['exemplify'], d_n, simulate_root=True)


@pytest.mark.usefixtures('mini_db')
def test_res():
    w = wn.Wordnet('test-en')
    ss = get_synsets(w)
    assert (sim.res(ss['information'], ss['information'], ic)
            == infocont(ss['information'], ic))
    assert (sim.res(ss['information'], ss['example'], ic)
            == infocont(ss['information'], ic))
    assert (sim.res(ss['information'], ss['sample'], ic)
            == infocont(ss['information'], ic))
    assert (sim.res(ss['information'], ss['random sample'], ic)
            == infocont(ss['information'], ic))
    assert (sim.res(ss['random sample'], ss['datum'], ic)
            == infocont(ss['information'], ic))
    with pytest.raises(wn.Error):
        sim.res(ss['random sample2'], ss['datum'], ic)
    with pytest.raises(wn.Error):
        sim.res(ss['example'], ss['exemplify'], ic)


@pytest.mark.usefixtures('mini_db')
def test_jcn():
    w = wn.Wordnet('test-en')
    ss = get_synsets(w)
    info_ic = infocont(ss['information'], ic)
    assert (sim.jcn(ss['information'], ss['information'], ic)
            == float('inf'))
    assert (sim.jcn(ss['information'], ss['example'], ic)
            == float('inf'))
    assert (sim.jcn(ss['information'], ss['sample'], ic)
            == 1 / ((info_ic + infocont(ss['sample'], ic)) - 2 * info_ic))
    assert (sim.jcn(ss['information'], ss['random sample'], ic)
            == 1 / ((info_ic + infocont(ss['random sample'], ic)) - 2 * info_ic))
    assert (sim.jcn(ss['random sample'], ss['datum'], ic)
            == 1 / (
                (infocont(ss['random sample'], ic) + infocont(ss['datum'], ic))
                - 2 * info_ic))
    with pytest.raises(wn.Error):
        sim.jcn(ss['random sample2'], ss['datum'], ic)
    with pytest.raises(wn.Error):
        sim.jcn(ss['example'], ss['exemplify'], ic)


@pytest.mark.usefixtures('mini_db')
def test_lin():
    w = wn.Wordnet('test-en')
    ss = get_synsets(w)
    info_ic = infocont(ss['information'], ic)
    assert (sim.lin(ss['information'], ss['information'], ic)
            == 1.0)
    assert (sim.lin(ss['information'], ss['example'], ic)
            == 1.0)
    assert (sim.lin(ss['information'], ss['sample'], ic)
            == (2 * info_ic) / (info_ic + infocont(ss['sample'], ic)))
    assert (sim.lin(ss['information'], ss['random sample'], ic)
            == (2 * info_ic) / (info_ic + infocont(ss['random sample'], ic)))
    assert (sim.lin(ss['random sample'], ss['datum'], ic)
            == ((2 * info_ic)
                / (infocont(ss['random sample'], ic) + infocont(ss['datum'], ic))))
    with pytest.raises(wn.Error):
        sim.lin(ss['random sample2'], ss['datum'], ic)
    with pytest.raises(wn.Error):
        sim.lin(ss['example'], ss['exemplify'], ic)
