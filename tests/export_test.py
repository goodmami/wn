import re
from xml.etree import ElementTree as ET

import pytest

import wn


@pytest.mark.usefixtures("mini_db")
def test_export(datadir, tmp_path):
    tmpdir = tmp_path / "test_export"
    tmpdir.mkdir()
    tmppath = tmpdir / "mini_lmf_export.xml"
    lexicons = wn.lexicons(lexicon="test-en test-es")
    wn.export(lexicons, tmppath, version="1.0")

    # remove comments, indentation, etc.
    orig = ET.canonicalize(from_file=datadir / "mini-lmf-1.0.xml", strip_text=True)
    temp = ET.canonicalize(from_file=tmppath, strip_text=True)
    # additional transformation to help with debugging
    orig = orig.replace("<", "\n<")
    temp = temp.replace("<", "\n<")
    assert orig == temp


@pytest.mark.usefixtures("mini_db_1_4")
def test_export_1_4(datadir, tmp_path):
    tmpdir = tmp_path / "test_export_1_4"
    tmpdir.mkdir()
    tmppath = tmpdir / "mini_lmf_export_1_4.xml"
    lexicons = wn.lexicons(lexicon="test-1.4")
    wn.export(lexicons, tmppath, version="1.4")

    # remove comments, indentation, etc.
    orig = ET.canonicalize(from_file=datadir / "mini-lmf-1.4.xml", strip_text=True)
    # temporary until support for exporting extensions
    orig = re.sub(r"\s*<LexiconExtension.*</LexiconExtension>\s*", "", orig, flags=re.M)
    temp = ET.canonicalize(from_file=tmppath, strip_text=True)
    # additional transformation to help with debugging
    orig = orig.replace("<", "\n<")
    temp = temp.replace("<", "\n<")
    assert orig == temp
