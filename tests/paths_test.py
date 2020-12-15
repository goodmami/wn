
import pytest

import wn


@pytest.mark.usefixtures('mini_db')
def test_hypernym_paths():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    assert information.hypernym_paths() == []
    assert example.hypernym_paths() == [[information]]
    assert sample.hypernym_paths() == [[example, information]]
    assert random_sample.hypernym_paths() == [[sample, example, information]]


@pytest.mark.usefixtures('mini_db')
def test_interlingual_hypernym_paths():
    información = wn.synsets('información')[0]
    ejemplo = wn.synsets('ejemplo')[0]
    inferred = wn.Synset.empty('*INFERRED*')
    muestra_aleatoria = wn.synsets('muestra aleatoria')[0]
    assert información.hypernym_paths() == []
    assert ejemplo.hypernym_paths() == [[información]]
    assert muestra_aleatoria.hypernym_paths() == [[inferred, ejemplo, información]]


@pytest.mark.usefixtures('mini_db')
def test_shortest_path():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    datum = wn.synsets('datum')[0]
    exemplify = wn.synsets('exemplify')[0]
    inferred_root = wn.Synset.empty('*INFERRED*')
    assert information.shortest_path(information) == []
    assert information.shortest_path(datum) == [datum]
    assert information.shortest_path(sample) == [example, sample]
    assert sample.shortest_path(information) == [example, information]
    assert random_sample.shortest_path(datum) == [sample, example, information, datum]
    with pytest.raises(wn.Error):
        example.shortest_path(exemplify)
    assert example.shortest_path(exemplify, simulate_root=True) == [
        information, inferred_root, exemplify
    ]


@pytest.mark.usefixtures('mini_db')
def test_min_depth():
    assert wn.synsets('information')[0].min_depth() == 0
    assert wn.synsets('example')[0].min_depth() == 1
    assert wn.synsets('sample')[0].min_depth() == 2
    assert wn.synsets('random sample')[0].min_depth() == 3


@pytest.mark.usefixtures('mini_db')
def test_max_depth():
    assert wn.synsets('information')[0].max_depth() == 0
    assert wn.synsets('example')[0].max_depth() == 1
    assert wn.synsets('sample')[0].max_depth() == 2
    assert wn.synsets('random sample')[0].max_depth() == 3
