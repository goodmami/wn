from typing import Callable, Optional

import wn
from wn._util import split_lexicon_specifier

SensekeyGetter = Callable[[wn.Sense], Optional[str]]
SenseGetter = Callable[[str], Optional[wn.Sense]]

METADATA_LEXICONS = {
    # OMW 1.4
    'omw-en:1.4',
    'omw-en31:1.4',
    # OMW 2.0
    'omw-en15:2.0',
    'omw-en16:2.0',
    'omw-en17:2.0',
    'omw-en171:2.0',
    'omw-en20:2.0',
    'omw-en21:2.0',
    'omw-en:2.0',
    'omw-en31:2.0',
    # EWN (OEWN) 2019, 2020
    'ewn:2019',
    'ewn:2020',
}

SENSE_ID_LEXICONS = {
    'oewn:2021',
    'oewn:2022',
    'oewn:2023',
    'oewn:2024',
}

OEWN_LEMMA_UNESCAPE_SEQUENCES = [
    ('-ap-', "'"),
    ('-ex-', '!'),
    ('-cm-', ','),
    ('-cn-', ':'),
    ('-pl-', '+'),
    ('-sl-', '/'),
]


def sensekey_getter(lexicon: str) -> SensekeyGetter:
    if lexicon in METADATA_LEXICONS:

        def getter(sense: wn.Sense) -> Optional[str]:
            return sense.metadata().get('identifier')

    elif lexicon in SENSE_ID_LEXICONS:
        lexid, _ = split_lexicon_specifier(lexicon)
        prefix_len = len(lexid) + 1

        def getter(sense: wn.Sense) -> Optional[str]:
            sensekey = sense.id[prefix_len:]
            # check if sense id is likely an escaped sensekey
            if '__' in sensekey:
                return unescape_oewn_sense_key(sense.id[prefix_len:])
            return None

    else:
        raise wn.Error(f'no sensekey getter is defined for {lexicon}')

    return getter


def unescape_oewn_sense_key(sense_key: str) -> str:
    lemma, _, rest = sense_key.partition('__')
    for esc, char in OEWN_LEMMA_UNESCAPE_SEQUENCES:
        lemma = lemma.replace(esc, char)
    rest = rest.replace('.', ':').replace('-sp-', '_')
    if rest:
        return f'{lemma}%{rest}'
    else:
        return lemma


def escape_oewn_sense_key(sense_key: str) -> str:
    lemma, _, rest = sense_key.partition('%')
    for esc, char in OEWN_LEMMA_UNESCAPE_SEQUENCES:
        lemma = lemma.replace(char, esc)
    rest = rest.replace(':', '.').replace('_', '-sp-')
    if rest:
        return f'{lemma}__{rest}'
    else:
        return lemma


def sense_getter(lexicon: str, wordnet: Optional[wn.Wordnet] = None) -> SenseGetter:
    if wordnet is None:
        wordnet = wn.Wordnet(lexicon)

    if lexicon in METADATA_LEXICONS:
        get_sensekey = sensekey_getter(lexicon)
        sensekey_map = {get_sensekey(s): s for s in wordnet.senses()}
        if None in sensekey_map:
            sensekey_map.pop(None)  # senses without sense keys

        def getter(sensekey: str) -> Optional[wn.Sense]:
            return sensekey_map.get(sensekey)

    elif lexicon in SENSE_ID_LEXICONS:
        lexid, _ = split_lexicon_specifier(lexicon)

        def getter(sensekey: str) -> Optional[wn.Sense]:
            sense_id = f'{lexid}-{escape_oewn_sense_key(sensekey)}'
            try:
                return wordnet.sense(sense_id)
            except wn.Error:
                return None

    else:
        raise wn.Error(f'no sense getter is defined for {lexicon}')

    return getter
