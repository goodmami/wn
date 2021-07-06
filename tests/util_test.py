
from wn import util


def test_synset_id_formatter():
    f = util.synset_id_formatter
    assert f()(prefix='xyz', offset=123, pos='n') == 'xyz-00000123-n'
    assert f(prefix='xyz')(offset=123, pos='n') == 'xyz-00000123-n'
    assert f(prefix='xyz', pos='n')(offset=123) == 'xyz-00000123-n'
    assert f('abc-{offset}-{pos}')(offset=1, pos='v') == 'abc-1-v'
