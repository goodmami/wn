import pytest

import wn
from wn.compat import sensekey


def test_unescape_oewn_sense_key():

    def unescape(s: str) -> str:
        return sensekey.unescape(s, flavor="oewn")

    assert unescape("") == ""
    assert unescape("abc") == "abc"
    assert unescape(".") == "."  # only becomes : in second part of key
    # escape patterns
    assert unescape("-ap-") == "'"
    assert unescape("-ex-") == "!"
    assert unescape("-cm-") == ","
    assert unescape("-cn-") == ":"
    assert unescape("-pl-") == "+"
    assert unescape("-sl-") == "/"
    # adjacent escapes need their own dashes
    assert unescape("-ap-ex-") == "'ex-"
    assert unescape("-ap--ex-") == "'!"
    # invalid escapes are unchanged
    assert unescape("-foo-") == "-foo-"  # not an escape sequence
    assert unescape("-sp-") == "-sp-"  # not valid in lemma portion
    assert unescape("ap-") == "ap-"  # no preceding dash
    assert unescape("-ap") == "-ap"  # no trailing dash
    assert unescape("-AP-") == "-AP-"  # case sensitivity
    # idempotency
    assert unescape(unescape("-ap--ex--cm-")) == unescape("-ap--ex--cm-")
    # full key, second part escapes differently
    assert unescape("abc__1.23.00..") == "abc%1:23:00::"
    assert unescape("abc__1.23.00.foo-sp-bar.") == "abc%1:23:00:foo_bar:"
    assert unescape("abc__1.23.00.foo-ap-bar.") == "abc%1:23:00:foo-ap-bar:"


def test_escape_oewn_sense_key():

    def escape(s: str) -> str:
        return sensekey.escape(s, flavor="oewn")

    assert escape("") == ""
    assert escape("abc") == "abc"
    assert escape(".") == "."  # only becomes : in second part of key
    # escape patterns
    assert escape("'") == "-ap-"
    assert escape("!") == "-ex-"
    assert escape(",") == "-cm-"
    assert escape(":") == "-cn-"
    assert escape("+") == "-pl-"
    assert escape("/") == "-sl-"
    # adjacent escapes need their own dashes
    assert escape("'!") == "-ap--ex-"
    # idempotency
    assert escape(escape("'!,")) == escape("'!,")
    # full key, second part escapes differently
    assert escape("abc%1:23:00::") == "abc__1.23.00.."
    assert escape("abc%1:23:00:foo_bar:") == "abc__1.23.00.foo-sp-bar."
    assert escape("abc%1:23:00:foo'bar:") == "abc__1.23.00.foo'bar."


@pytest.mark.usefixtures("uninitialized_datadir")
def test_sense_key_getter(datadir):
    wn.add(datadir / "sense-key-variations.xml")

    get_omw_sense_key = sensekey.sense_key_getter("omw-en:1.4")
    get_oewn_sense_key = sensekey.sense_key_getter("oewn:2024")

    omw_sense = wn.sense("omw-en--apos-s_Gravenhage-08950407-n", lexicon="omw-en:1.4")
    oewn_sense = wn.sense("oewn--ap-s_gravenhage__1.15.00..", lexicon="oewn:2024")

    assert get_omw_sense_key(omw_sense) == "'s_gravenhage%1:15:00::"
    assert get_omw_sense_key(oewn_sense) is None

    assert get_oewn_sense_key(omw_sense) is None
    assert get_oewn_sense_key(oewn_sense) == "'s_gravenhage%1:15:00::"


@pytest.mark.usefixtures("uninitialized_datadir")
def test_sense_getter(datadir):
    wn.add(datadir / "sense-key-variations.xml")

    get_omw_sense = sensekey.sense_getter("omw-en:1.4")
    get_oewn_sense = sensekey.sense_getter("oewn:2024")

    omw_sense = wn.sense("omw-en--apos-s_Gravenhage-08950407-n", lexicon="omw-en:1.4")
    oewn_sense = wn.sense("oewn--ap-s_gravenhage__1.15.00..", lexicon="oewn:2024")

    assert get_omw_sense("'s_gravenhage%1:15:00::") == omw_sense
    assert get_oewn_sense("'s_gravenhage%1:15:00::") == oewn_sense
