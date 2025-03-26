import wn
from wn import lmf

import pytest


@pytest.mark.benchmark(group="lmf.load", warmup=True)
def test_load(datadir, benchmark):
    benchmark(lmf.load, datadir / 'mini-lmf-1.0.xml')


@pytest.mark.benchmark(group="wn.add_lexical_resource")
@pytest.mark.usefixtures('empty_db')
def test_add_lexical_resource(mock_lmf, benchmark):
    # TODO: when pytest-benchmark's teardown option is released, use
    # that here with more rounds
    benchmark.pedantic(
        wn.add_lexical_resource,
        args=(mock_lmf,),
        # teardown=clean_db,
        iterations=1,
        rounds=1,
    )


@pytest.mark.benchmark(group="wn.add_lexical_resource")
@pytest.mark.usefixtures('empty_db')
def test_add_lexical_resource_no_progress(mock_lmf, benchmark):
    # TODO: when pytest-benchmark's teardown option is released, use
    # that here with more rounds
    benchmark.pedantic(
        wn.add_lexical_resource,
        args=(mock_lmf,),
        kwargs={"progress_handler": None},
        # teardown=clean_db,
        iterations=1,
        rounds=1,
    )


@pytest.mark.benchmark(group="primary queries")
@pytest.mark.usefixtures('mock_db')
def test_synsets(mock_db, benchmark):
    benchmark(wn.synsets)


@pytest.mark.benchmark(group="primary queries")
@pytest.mark.usefixtures('mock_db')
def test_words(mock_db, benchmark):
    benchmark(wn.words)
