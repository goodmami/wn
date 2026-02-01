from typing import Literal, overload

from wn._config import config
from wn._core import Form, Sense, Synset, Word
from wn._db import clear_connections, connect, list_lexicons_safe
from wn._download import download
from wn._exceptions import Error
from wn._lexicon import Lexicon
from wn._util import format_lexicon_specifier
from wn._wordnet import Wordnet


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
        >>> infos[0]["label"]
        'Open English WordNet'

    """
    index = config.index
    return [
        config.get_project_info(format_lexicon_specifier(project_id, version))
        for project_id, project_info in index.items()
        for version in project_info.get("versions", [])
        if "resource_urls" in project_info["versions"][version]
    ]


def lexicons(*, lexicon: str | None = "*", lang: str | None = None) -> list[Lexicon]:
    """Return the lexicons matching a language or lexicon specifier.

    Example:

        >>> wn.lexicons(lang="en")
        [<Lexicon ewn:2020 [en]>, <Lexicon omw-en:1.4 [en]>]

    """
    try:
        w = Wordnet(lang=lang, lexicon=lexicon or "*")
    except Error:
        return []
    else:
        return w.lexicons()


def reset_database(rebuild: bool = False) -> None:
    """Delete and recreate the database file.

    If *rebuild* is :python:`True`, Wn will attempt to add all lexicons
    that are added in the existing database. Note that this will only
    attempt to add indexed projects via their lexicon specifiers, (using
    :python:`wn.download(specifier)`) regardless of how they were
    originally added, and will not attempt to add resources from
    unindexed URLs or local files (unless those local files are cached
    versions of indexed resources).

    This function is useful when database schema changes necessitate a
    rebuild or when testing requires a clean database.

    .. warning::
       This will completely delete the database and all added resources.
       It does not delete the download cache. Using ``rebuild=True``
       does not re-add non-lexicon resources like CILI files or
       unindexed resources, so you will need to add those manually.
    """
    specs = list_lexicons_safe()
    clear_connections()
    config.database_path.unlink(missing_ok=True)
    connect()
    if rebuild:
        for spec in specs:
            download(spec)
    clear_connections()


def word(id: str, *, lexicon: str | None = None, lang: str | None = None) -> Word:
    """Return the word with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.word` method.

    >>> wn.word("ewn-cell-n")
    Word('ewn-cell-n')

    """
    return Wordnet(lang=lang, lexicon=lexicon).word(id)


def words(
    form: str | None = None,
    pos: str | None = None,
    *,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[Word]:
    """Return the list of matching words.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.words` method.

    >>> len(wn.words())
    282902
    >>> len(wn.words(pos="v"))
    34592
    >>> wn.words(form="scurry")
    [Word('ewn-scurry-n'), Word('ewn-scurry-v')]

    """
    return Wordnet(lang=lang, lexicon=lexicon).words(form=form, pos=pos)


@overload
def lemmas(
    form: str | None = None,
    pos: str | None = None,
    *,
    data: Literal[False] = False,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[str]: ...


@overload
def lemmas(
    form: str | None = None,
    pos: str | None = None,
    *,
    data: Literal[True] = True,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[Form]: ...


@overload
def lemmas(
    form: str | None = None,
    pos: str | None = None,
    *,
    data: bool,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[str] | list[Form]: ...


def lemmas(
    form: str | None = None,
    pos: str | None = None,
    *,
    data: bool = False,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[str] | list[Form]:
    """Return the list of lemmas for matching words.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.lemmas` method.

    If the *data* argument is :python:`False` (the default), the
    lemmas are returned as :class:`str` types. If it is
    :python:`True`, :class:`wn.Form` objects are used instead.

    >>> wn.lemmas("wolves")
    ['wolf']
    >>> wn.lemmas("wolves", data=True)
    [Form(value='wolf')]
    >>> len(wn.lemmas(pos="v"))
    11617

    """
    return Wordnet(lang=lang, lexicon=lexicon).lemmas(form=form, pos=pos, data=data)


def synset(id: str, *, lexicon: str | None = None, lang: str | None = None) -> Synset:
    """Return the synset with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.synset` method.

    >>> wn.synset("ewn-03311152-n")
    Synset('ewn-03311152-n')

    """
    return Wordnet(lang=lang, lexicon=lexicon).synset(id=id)


def synsets(
    form: str | None = None,
    pos: str | None = None,
    ili: str | None = None,
    *,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[Synset]:
    """Return the list of matching synsets.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.synsets` method.

    >>> len(wn.synsets("couch"))
    4
    >>> wn.synsets("couch", pos="v")
    [Synset('ewn-00983308-v')]

    """
    return Wordnet(lang=lang, lexicon=lexicon).synsets(form=form, pos=pos, ili=ili)


def senses(
    form: str | None = None,
    pos: str | None = None,
    *,
    lexicon: str | None = None,
    lang: str | None = None,
) -> list[Sense]:
    """Return the list of matching senses.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The remaining arguments are passed to the
    :meth:`Wordnet.senses` method.

    >>> len(wn.senses("twig"))
    3
    >>> wn.senses("twig", pos="n")
    [Sense('ewn-twig-n-13184889-02')]

    """
    return Wordnet(lang=lang, lexicon=lexicon).senses(form=form, pos=pos)


def sense(id: str, *, lexicon: str | None = None, lang: str | None = None) -> Sense:
    """Return the sense with *id* in *lexicon*.

    This will create a :class:`Wordnet` object using the *lang* and
    *lexicon* arguments. The *id* argument is then passed to the
    :meth:`Wordnet.sense` method.

    >>> wn.sense("ewn-flutter-v-01903884-02")
    Sense('ewn-flutter-v-01903884-02')

    """
    return Wordnet(lang=lang, lexicon=lexicon).sense(id=id)
