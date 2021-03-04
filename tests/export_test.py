
from xml.etree import ElementTree as ET

import pytest

import wn


@pytest.mark.usefixtures('mini_db')
def test_export(mini_lmf_1_0, tmp_path):
    tmpdir = tmp_path / 'test_export'
    tmpdir.mkdir()
    tmppath = tmpdir / 'mini_lmf_export.xml'
    lexicons = wn.lexicons(lexicon='test-en test-es')
    wn.export(lexicons, tmppath)

    if hasattr(ET, 'canonicalize'):  # available from Python 3.8
        # remove comments, indentation, etc.
        orig = ET.canonicalize(from_file=mini_lmf_1_0, strip_text=True)
        temp = ET.canonicalize(from_file=tmppath, strip_text=True)
        # additional transformation to help with debugging
        orig = orig.replace('<', '\n<')
        temp = temp.replace('<', '\n<')
        assert orig == temp
