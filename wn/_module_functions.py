from typing import Literal, Optional, Union, overload

import wn
from wn._util import format_lexicon_specifier


def projects() -> list[dict]:
    """Return the list of indexed projects.

    This returns the same dictionaries of information as
    :meth:`wn.config.get_project_info
    <wn._config.WNConfig.get_project_info>`, but for all indexed
    projects.

    Example:

        >>> infos = wn.projects()
        >>> len(infos)
        36
        >>> infos[0]['label']
        'Open English WordNet'

    """
    index = wn.config.index
    return [
        wn.config.get_project_info(format_lexicon_specifier(project_id, version))
        for project_id, project_info in index.items()
        for version in project_info.get('versions', [])
        if 'resource_urls' in project_info['versions'][version]
    ]


def lexicons(
    *,
    lexicon: Optional[str] = "*",
    lang: Optional[str] = None
) -> list[wn.Lexicon]:
    """Return the lexicons matching a language or lexicon specifier.

    Example:

        >>> wn.lexicons(lang='en')
        [<Lexicon ewn:2020 [en]>, <Lexicon omw-en:1.4 [en]>]

    """
    try:
        w = wn.Wordnet(lang=lang, lexicon=lexicon or '*')
    except wn.Error:
        return []
    else:
        return w.lexicons()


def word(
    id: str,
    *,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None
) -> wn.Word:
    """Return the word with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.word` method.

    >>> wn.word('ewn-cell-n')
    Word('ewn-cell-n')

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).word(id)


def words(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    *,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> list[wn.Word]:
    """Return the list of matching words.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.words` method.

    >>> len(wn.words())
    282902
    >>> len(wn.words(pos='v'))
    34592
    >>> wn.words(form="scurry")
    [Word('ewn-scurry-n'), Word('ewn-scurry-v')]

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).words(form=form, pos=pos)


@overload
def lemmas(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    *,
    data: Literal[False] = False,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> list[str]: ...


@overload
def lemmas(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    *,
    data: Literal[True] = True,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> list[wn.Form]: ...


@overload
def lemmas(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    *,
    data: bool,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> Union[list[str], list[wn.Form]]: ...


def lemmas(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    *,
    data: bool = False,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> Union[list[str], list[wn.Form]]:
    """Return the list of lemmas for matching words.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.lemmas` method.

    If the *data* argument is :python:`False` (the default), the
    lemmas are returned as :class:`str` types. If it is
    :python:`True`, :class:`wn.Form` objects are used instead.

    >>> wn.lemmas('wolves')
    ['wolf']
    >>> wn.lemmas('wolves', data=True)
    [Form(value='wolf')]
    >>> len(wn.lemmas(pos='v'))
    11617

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).lemmas(form=form, pos=pos, data=data)


def synset(
    id: str,
    *,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None
) -> wn.Synset:
    """Return the synset with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.synset` method.

    >>> wn.synset('ewn-03311152-n')
    Synset('ewn-03311152-n')

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).synset(id=id)


def synsets(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    ili: Optional[str] = None,
    *,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> list[wn.Synset]:
    """Return the list of matching synsets.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.synsets` method.

    >>> len(wn.synsets('couch'))
    4
    >>> wn.synsets('couch', pos='v')
    [Synset('ewn-00983308-v')]

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).synsets(form=form, pos=pos, ili=ili)


def senses(
    form: Optional[str] = None,
    pos: Optional[str] = None,
    *,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None,
) -> list[wn.Sense]:
    """Return the list of matching senses.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.senses` method.

    >>> len(wn.senses('twig'))
    3
    >>> wn.senses('twig', pos='n')
    [Sense('ewn-twig-n-13184889-02')]

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).senses(form=form, pos=pos)


def sense(
    id: str,
    *,
    lexicon: Optional[str] = None,
    lang: Optional[str] = None
) -> wn.Sense:
    """Return the sense with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.sense` method.

    >>> wn.sense('ewn-flutter-v-01903884-02')
    Sense('ewn-flutter-v-01903884-02')

    """
    return wn.Wordnet(lang=lang, lexicon=lexicon).sense(id=id)
