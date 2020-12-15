
import pytest

import wn
from wn import similarity as sim


@pytest.mark.usefixtures('mini_db')
def test_path():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    datum = wn.synsets('datum')[0]
    exemplify = wn.synsets('exemplify')[0]
    assert sim.path(information, information) == 1/1
    assert sim.path(information, example) == 1/2
    assert sim.path(information, sample) == 1/3
    assert sim.path(information, random_sample) == 1/4
    assert sim.path(random_sample, datum) == 1/5
    assert sim.path(example, exemplify) == 1/4


@pytest.mark.usefixtures('mini_db')
def test_wup():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    datum = wn.synsets('datum')[0]
    exemplify = wn.synsets('exemplify')[0]
    assert sim.wup(information, information) == (2*1) / (0+0+2*1)
    assert sim.wup(information, example) == (2*1) / (0+1+2*1)
    assert sim.wup(information, sample) == (2*1) / (0+2+2*1)
    assert sim.wup(information, random_sample) == (2*1) / (0+3+2*1)
    assert sim.wup(random_sample, datum) == (2*1) / (3+1+2*1)
    assert sim.wup(example, exemplify) == (2*1) / (2+1+2*1)
