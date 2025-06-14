"""Functions Related to Sense Keys

Sense keys are identifiers of senses that (mostly) persist across
wordnet versions. They are only used by the English wordnets. For the
OMW lexicons derived from the Princeton WordNet and the EWN 2019/2020
lexicons, the sense key is encoded in the ``identifier`` metadata of a
Sense:

>>> import wn
>>> en = wn.Wordnet("omw-en:1.4")
>>> sense = en.sense("omw-en-carrousel-02966372-n")
>>> sense.metadata()
{'identifier': 'carrousel%1:06:01::'}

For OEWN 2021+ lexicons, the sense key is encoded in the sense ID, but
some characters are escaped or replaced to ensure it is a valid XML
ID.

>>> oewn = wn.Wordnet("oewn:2024")
>>> sense = oewn.sense("oewn-carousel__1.06.01..")
>>> sense.id
'oewn-carousel__1.06.01..'

This module has four functions:

1. :func:`escape` transforms a sense key into a form that is valid for
   XML IDs. The *flavor* keyword argument specifies the escaping
   mechanism and it defaults to "oewn", which is currently the only
   available flavor.

2. :func:`unescape` transforms an escaped sense key back into the
   original form. The *flavor* keyword is the same as with
   :func:`escape`.

3. :func:`sense_key_getter` creates a function for retrieving the
   sense key for a given :class:`wn.Sense` object. Depending on the
   lexicon, it will retrieve the sense key from metadata or it will
   unescape the sense ID.

4. :func:`sense_getter` creates a function for retrieving a
   :class:`wn.Sense` object given a sense key. Depending on the
   lexicon, it will build and use a mapping of sense key metadata to
   :class:`wn.Sense` objects, or it will escape the sense key and use
   the escaped form as the ``id`` argument for
   :meth:`wn.Wordnet.sense`.

.. seealso::

   The documentation from the Princeton WordNet:
   https://wordnet.princeton.edu/documentation/senseidx5wn

"""

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

SENSE_ID_LEXICONS = {  # specifier:flavor
    'oewn:2021': "oewn",
    'oewn:2022': "oewn",
    'oewn:2023': "oewn",
    'oewn:2024': "oewn",
}

OEWN_LEMMA_UNESCAPE_SEQUENCES = [
    ('-ap-', "'"),
    ('-ex-', '!'),
    ('-cm-', ','),
    ('-cn-', ':'),
    ('-pl-', '+'),
    ('-sl-', '/'),
]


def unescape(s: str, /, flavor="oewn") -> str:
    """Return the original form of an escaped sense key.

    The *flavor* argument specifies how the unescaping will be done.
    Its default (and currently only) value is "oewn", which escapes
    like the Open English Wordnet.

    >>> from wn.compat import sensekey
    >>> sensekey.unescape("ceramic__3.01.00..")
    'ceramic%3:01:00::'

    Note that this function does not remove any lexicon ID prefixes on
    sense IDs, so that may need to be done manually:

    >>> sensekey.unescape("oewn-ceramic__3.01.00..")
    'oewn-ceramic%3:01:00::'
    >>> sensekey.unescape("oewn-ceramic__3.01.00..".removeprefix("oewn-"))
    'ceramic%3:01:00::'

    """
    if flavor == "oewn":
        return _unescape_oewn(s)
    else:
        raise ValueError(f"unsupported flavor: {flavor}")


def _unescape_oewn(s: str) -> str:
    lemma, _, rest = s.partition('__')
    for esc, char in OEWN_LEMMA_UNESCAPE_SEQUENCES:
        lemma = lemma.replace(esc, char)
    rest = rest.replace('.', ':').replace('-sp-', '_')
    if rest:
        return f'{lemma}%{rest}'
    else:
        return lemma


def escape(sense_key: str, /, flavor="oewn") -> str:
    """Return an escaped sense key that is valid for XML IDs.

    The *flavor* argument specifies how the escaping will be done. Its
    default (and currently only) value is "oewn", which escapes like
    the Open English Wordnet.

    >>> from wn.compat import sensekey
    >>> sensekey.escape("ceramic%3:01:00::")
    'ceramic__3.01.00..'

    """
    if flavor == "oewn":
        return _escape_oewn(sense_key)
    else:
        raise ValueError(f"unsupported flavor: {flavor}")


def _escape_oewn(sense_key: str) -> str:
    lemma, _, rest = sense_key.partition('%')
    for esc, char in OEWN_LEMMA_UNESCAPE_SEQUENCES:
        lemma = lemma.replace(char, esc)
    rest = rest.replace(':', '.').replace('_', '-sp-')
    if rest:
        return f'{lemma}__{rest}'
    else:
        return lemma


def sense_key_getter(lexicon: str) -> SensekeyGetter:
    """Return a function that gets sense keys from senses.

    The *lexicon* argument determines how the function will retrieve
    the sense key; i.e., whether it is from the ``identifier``
    metadata or unescaping the sense ID. For any unsupported lexicon,
    an error is raised.

    The function that is returned accepts one argument, a
    :class:`wn.Sense` (ideally from the same lexicon specified in the
    *lexicon* argument), and returns a :class:`str` if the sense key
    exists in the lexicon or :data:`None` otherwise.

    >>> import wn
    >>> from wn.compat import sensekey
    >>> oewn = wn.Wordnet("oewn:2024")
    >>> get_sense_key = sensekey.sense_key_getter("oewn:2024")
    >>> get_sense_key(oewn.senses("alabaster")[0])
    'alabaster%3:01:00::'

    When unescaping a sense ID, if the ID starts with its lexicon's ID
    and a hyphen (e.g., `"oewn-"`), it is assumed to be a conventional
    ID prefix and is removed prior to unescaping.

    """
    if lexicon in METADATA_LEXICONS:

        def getter(sense: wn.Sense) -> Optional[str]:
            return sense.metadata().get('identifier')

    elif lexicon in SENSE_ID_LEXICONS:
        flavor = SENSE_ID_LEXICONS[lexicon]
        lexid, _ = split_lexicon_specifier(lexicon)
        prefix = f"{lexid}-"

        def getter(sense: wn.Sense) -> Optional[str]:
            sense_key = sense.id.removeprefix(prefix)
            # check if sense id is likely an escaped sense key
            if '__' in sense_key:
                return unescape(sense_key, flavor=flavor)
            return None

    else:
        raise wn.Error(f'no sense key getter is defined for {lexicon}')

    return getter


def sense_getter(lexicon: str, wordnet: Optional[wn.Wordnet] = None) -> SenseGetter:
    """Return a function that gets the sense for a sense key.

    The *lexicon* argument determines how the function will retrieve
    the sense; i.e., whether a mapping between a sense's
    ``identifier`` metadata and the sense will be created and used or
    the escaped sense key is used as the sense ID. For any unsupported
    lexicon, an error is raised.

    The optional *wordnet* object is used as the source of the
    returned :class:`wn.Sense` objects. If none is provided, a new
    :class:`wn.Wordnet` object is created using the *lexicon*
    argument.

    The function that is returned accepts one argument, a :class:`str`
    of the sense key, and returns a :class:`wn.Sense` if the sense key
    exists in the lexicon or :data:`None` otherwise.

    >>> import wn
    >>> from wn.compat import sensekey
    >>> get_sense = sensekey.sense_getter("oewn:2024")
    >>> get_sense("alabaster%3:01:00::")
    Sense('oewn-alabaster__3.01.00..')

    .. warning::

       The mapping built for the ``omw-en*`` or ``ewn`` lexicons
       requires significant memory---around 100MiB---to use. The
       ``oewn`` lexicons do not require such a mapping and the memory
       usage is negligible.

    """
    if wordnet is None:
        wordnet = wn.Wordnet(lexicon)

    if lexicon in METADATA_LEXICONS:
        get_sense_key = sense_key_getter(lexicon)
        sense_key_map = {get_sense_key(s): s.id for s in wordnet.senses()}
        if None in sense_key_map:
            sense_key_map.pop(None)  # senses without sense keys

        def getter(sense_key: str) -> Optional[wn.Sense]:
            if sense_id := sense_key_map.get(sense_key):
                return wordnet.sense(sense_id)
            return None

    elif lexicon in SENSE_ID_LEXICONS:
        flavor = SENSE_ID_LEXICONS[lexicon]
        lexid, _ = split_lexicon_specifier(lexicon)

        def getter(sense_key: str) -> Optional[wn.Sense]:
            sense_id = f'{lexid}-{escape(sense_key, flavor=flavor)}'
            try:
                return wordnet.sense(sense_id)
            except wn.Error:
                return None

    else:
        raise wn.Error(f'no sense getter is defined for {lexicon}')

    return getter
