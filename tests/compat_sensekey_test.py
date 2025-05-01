import pytest

import wn
from wn.compat import sensekey


@pytest.mark.usefixtures("uninitialized_datadir")
def test_sensekey_getter(datadir):
    wn.add(datadir / "sensekey-variations.xml")

    get_omw_sensekey = sensekey.sensekey_getter("omw-en:1.4")
    get_oewn_sensekey = sensekey.sensekey_getter("oewn:2024")

    omw_sense = wn.sense("omw-en--apos-s_Gravenhage-08950407-n", lexicon='omw-en:1.4')
    oewn_sense = wn.sense("oewn--ap-s_gravenhage__1.15.00..", lexicon='oewn:2024')

    assert get_omw_sensekey(omw_sense) == "'s_gravenhage%1:15:00::"
    assert get_omw_sensekey(oewn_sense) is None

    assert get_oewn_sensekey(omw_sense) is None
    assert get_oewn_sensekey(oewn_sense) == "'s_gravenhage%1:15:00::"
