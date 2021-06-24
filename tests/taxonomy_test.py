
import pytest

import wn
from wn.taxonomy import (
    roots,
    leaves,
    taxonomy_depth,
    hypernym_paths,
    min_depth,
    max_depth,
    shortest_path,
    common_hypernyms,
    lowest_common_hypernyms,
)


@pytest.mark.usefixtures('mini_db')
def test_roots():
    en = wn.Wordnet('test-en')
    assert set(roots(en, pos='n')) == {en.synset('test-en-0001-n'),
                                       en.synset('test-en-0008-n')}
    assert set(roots(en, pos='v')) == {en.synset('test-en-0003-v'),
                                       en.synset('test-en-0007-v')}
    assert roots(en, pos='a') == []
    assert set(roots(en)) == set(roots(en, pos='n') + roots(en, pos='v'))

    # with no expand relations and no relation of its own, every
    # synset looks like a root
    es = wn.Wordnet('test-es')
    assert set(roots(es, pos='n')) == {es.synset('test-es-0001-n'),
                                       es.synset('test-es-0002-n'),
                                       es.synset('test-es-0005-n')}

    es = wn.Wordnet('test-es', expand='test-en')
    assert roots(es, pos='n') == [es.synset('test-es-0001-n')]


@pytest.mark.usefixtures('mini_db')
def test_leaves():
    en = wn.Wordnet('test-en')
    assert set(leaves(en, pos='n')) == {en.synset('test-en-0005-n'),
                                        en.synset('test-en-0006-n'),
                                        en.synset('test-en-0008-n')}
    assert set(leaves(en, pos='v')) == {en.synset('test-en-0003-v'),
                                        en.synset('test-en-0007-v')}


@pytest.mark.usefixtures('mini_db')
def test_taxonomy_depth():
    en = wn.Wordnet('test-en')
    assert taxonomy_depth(en, pos='n') == 3
    assert taxonomy_depth(en, pos='v') == 0


@pytest.mark.usefixtures('mini_db')
def test_hypernym_paths():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    assert hypernym_paths(information) == []
    assert hypernym_paths(example) == [[information]]
    assert hypernym_paths(sample) == [[example, information]]
    assert hypernym_paths(random_sample) == [[sample, example, information]]


@pytest.mark.usefixtures('mini_db')
def test_interlingual_hypernym_paths():
    información = wn.synsets('información')[0]
    ejemplo = wn.synsets('ejemplo')[0]
    inferred = wn.Synset.empty('*INFERRED*')
    muestra_aleatoria = wn.synsets('muestra aleatoria')[0]
    assert hypernym_paths(información) == []
    assert hypernym_paths(ejemplo) == [[información]]
    assert hypernym_paths(muestra_aleatoria) == [[inferred, ejemplo, información]]


@pytest.mark.usefixtures('mini_db')
def test_shortest_path():
    information = wn.synsets('information')[0]
    example = wn.synsets('example')[0]
    sample = wn.synsets('sample')[0]
    random_sample = wn.synsets('random sample')[0]
    datum = wn.synsets('datum')[0]
    exemplify = wn.synsets('exemplify')[0]
    inferred_root = wn.Synset.empty('*INFERRED*')
    assert shortest_path(information, information) == []
    assert shortest_path(information, datum) == [datum]
    assert shortest_path(information, sample) == [example, sample]
    assert shortest_path(sample, information) == [example, information]
    assert shortest_path(random_sample, datum) == [sample, example, information, datum]
    with pytest.raises(wn.Error):
        shortest_path(example, exemplify)
    assert shortest_path(example, exemplify, simulate_root=True) == [
        information, inferred_root, exemplify
    ]


@pytest.mark.usefixtures('mini_db')
def test_min_depth():
    assert min_depth(wn.synsets('information')[0]) == 0
    assert min_depth(wn.synsets('example')[0]) == 1
    assert min_depth(wn.synsets('sample')[0]) == 2
    assert min_depth(wn.synsets('random sample')[0]) == 3


@pytest.mark.usefixtures('mini_db')
def test_max_depth():
    assert max_depth(wn.synsets('information')[0]) == 0
    assert max_depth(wn.synsets('example')[0]) == 1
    assert max_depth(wn.synsets('sample')[0]) == 2
    assert max_depth(wn.synsets('random sample')[0]) == 3
