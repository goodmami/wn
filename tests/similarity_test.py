
from math import log

import pytest

import wn
from wn import similarity as sim
from wn.taxonomy import taxonomy_depth


@pytest.mark.usefixtures('mini_db')
def test_path():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    random_sample2 = wn.synsets('random sample')[1]
    datum = wn.synsets('datum')[0]
    exemplify = wn.synsets('exemplify')[0]
    assert sim.path(information, information) == 1/1
    assert sim.path(information, example) == 1/2
    assert sim.path(information, sample) == 1/3
    assert sim.path(information, random_sample) == 1/4
    assert sim.path(random_sample, datum) == 1/5
    assert sim.path(random_sample2, datum) == 0
    assert sim.path(random_sample2, datum, simulate_root=True) == 1/4
    assert sim.path(random_sample, random_sample2, simulate_root=True) == 1/6
    with pytest.raises(wn.Error):
        sim.path(example, exemplify)
    with pytest.raises(wn.Error):
        sim.wup(example, exemplify, simulate_root=True)


@pytest.mark.usefixtures('mini_db')
def test_wup():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    random_sample2 = wn.synsets('random sample')[1]
    datum = wn.synsets('datum')[0]
    exemplify = wn.synsets('exemplify')[0]
    assert sim.wup(information, information) == (2*1) / (0+0+2*1)
    assert sim.wup(information, example) == (2*1) / (0+1+2*1)
    assert sim.wup(information, sample) == (2*1) / (0+2+2*1)
    assert sim.wup(information, random_sample) == (2*1) / (0+3+2*1)
    assert sim.wup(random_sample, datum) == (2*1) / (3+1+2*1)
    with pytest.raises(wn.Error):
        assert sim.wup(random_sample2, datum)
    assert (sim.wup(random_sample2, datum, simulate_root=True)
            == (2*1) / (1+2+2*1))
    assert (sim.wup(random_sample, random_sample2, simulate_root=True)
            == (2*1) / (4+1+2*1))
    with pytest.raises(wn.Error):
        sim.wup(example, exemplify)
    with pytest.raises(wn.Error):
        sim.wup(example, exemplify, simulate_root=True)


@pytest.mark.usefixtures('mini_db')
def test_lch():
    w = wn.Wordnet('test-en')
    d_n = taxonomy_depth(w, 'n')
    information = w.synsets('information')[0]
    example = w.synsets('example')[0]
    sample = w.synsets('sample')[0]
    random_sample = w.synsets('random sample')[0]
    random_sample2 = wn.synsets('random sample')[1]
    datum = w.synsets('datum')[0]
    exemplify = w.synsets('exemplify')[0]
    assert sim.lch(information, information, d_n) == -log((0+1) / (2*d_n))
    assert sim.lch(information, example, d_n) == -log((1+1) / (2*d_n))
    assert sim.lch(information, sample, d_n) == -log((2+1) / (2*d_n))
    assert sim.lch(information, random_sample, d_n) == -log((3+1) / (2*d_n))
    assert sim.lch(random_sample, datum, d_n) == -log((4+1) / (2*d_n))
    with pytest.raises(wn.Error):
        assert sim.lch(random_sample2, datum, d_n)
    assert (sim.lch(random_sample2, datum, d_n, simulate_root=True)
            == -log((3+1) / (2*d_n)))
    assert (sim.lch(random_sample, random_sample2, d_n, simulate_root=True)
            == -log((5+1) / (2*d_n)))
    with pytest.raises(wn.Error):
        sim.lch(example, exemplify, d_n)
    with pytest.raises(wn.Error):
        sim.lch(example, exemplify, d_n, simulate_root=True)
