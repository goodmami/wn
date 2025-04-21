
"""Web interface for Wn databases."""

from typing import Optional, Union
from functools import wraps
from urllib.parse import urlsplit, parse_qs, urlencode

from starlette.applications import Starlette  # type: ignore
from starlette.responses import JSONResponse  # type: ignore
from starlette.routing import Route  # type: ignore
from starlette.requests import Request  # type: ignore

import wn

DEFAULT_PAGINATION_LIMIT = 50


def paginate(proto):

    def paginate_wrapper(func):

        @wraps(func)
        async def _paginate_wrapper(request: Request) -> JSONResponse:
            url = str(request.url)
            query = dict(request.query_params)
            offset = abs(int(query.pop('page[offset]', 0)))
            limit = abs(int(query.pop('page[limit]', DEFAULT_PAGINATION_LIMIT)))

            obj = await func(request)
            total = len(obj['data'])
            prev = max(0, offset - limit)
            next = offset + limit
            last = (total//limit)*limit

            obj['data'] = [proto(x, request) for x in obj['data'][offset:offset+limit]]
            obj.setdefault('meta', {}).update(total=total)

            links = {}
            if offset > 0:
                links['first'] = replace_query_params(url, **{'page[offset]': 0})
                links['prev'] = replace_query_params(url, **{'page[offset]': prev})
            if next < total:
                links['next'] = replace_query_params(url, **{'page[offset]': next})
                links['last'] = replace_query_params(url, **{'page[offset]': last})
            if links:
                obj.setdefault('links', {}).update(links)

            return JSONResponse(obj)

        return _paginate_wrapper

    return paginate_wrapper


def replace_query_params(url: str, **params) -> str:
    u = urlsplit(url)
    q = parse_qs(u.query)
    q.update(params)
    qs = urlencode(q, doseq=True)
    return u._replace(query=qs).geturl()


# Wordnet-instantiation

def _init_wordnet(
    lexicon: str = '*',
    lang: Optional[str] = None,
) -> wn.Wordnet:
    if lexicon == '*' and lang is not None:
        lexicon = ' '.join(lex.specifier() for lex in wn.lexicons(lang=lang))
    return wn.Wordnet(lexicon)


# Data-making functions

def _url_for_obj(
    request: Request,
    name: str,
    obj: Union[wn.Word, wn.Sense, wn.Synset],
    lexicon: Optional[str] = None,
) -> str:
    if lexicon is None:
        lexicon = obj.lexicon().specifier()
    kwargs = {
        'lexicon': lexicon,
        name: obj.id
    }
    return str(request.url_for(name, **kwargs))


def make_lexicon(lex: wn.Lexicon, request: Request) -> dict:
    spec = lex.specifier()
    return {
        'id': spec,
        'type': 'lexicon',
        'attributes': {
            # cannot have 'id' as JSON:API disallows it
            'version': lex.version,
            'label': lex.label,
            'language': lex.language,
            'license': lex.license,
        },
        'links': {
            'self': str(request.url_for('lexicon', lexicon=spec))
        },
        'relationships': {
            'words': {
                'links': {'related': str(request.url_for('words', lexicon=spec))},
            },
            'synsets': {
                'links': {'related': str(request.url_for('synsets', lexicon=spec))},
            },
            'senses': {
                'links': {'related': str(request.url_for('senses', lexicon=spec))},
            },
        }
    }


def make_word(w: wn.Word, request: Request, basic: bool = False) -> dict:
    lex_spec = w.lexicon().specifier()
    d: dict = {
        'id': w.id,
        'type': 'word',
        'attributes': {
            'pos': w.pos,
            'lemma': w.lemma(),
            'forms': w.forms(),
        },
        'links': {
            'self': _url_for_obj(request, 'word', w, lexicon=lex_spec)
        }
    }
    if not basic:
        synsets = w.synsets()
        lex_link = str(request.url_for('lexicon', lexicon=lex_spec))
        senses_link = str(request.url_for('senses', word=w.id, lexicon=lex_spec))
        d.update({
            'relationships': {
                'senses': {'links': {'related': senses_link}},
                'synsets': {'data': [dict(type='synset', id=ss.id) for ss in synsets]},
                'lexicon': {'links': {'related': lex_link}}
            },
            'included': [make_synset(ss, request, basic=True) for ss in synsets]
        })
    return d


def make_sense(s: wn.Sense, request: Request, basic: bool = False) -> dict:
    lex_spec = s.lexicon().specifier()
    d: dict = {
        'id': s.id,
        'type': 'sense',
        'links': {
            'self': _url_for_obj(request, 'sense', s, lexicon=lex_spec)
        }
    }
    if not basic:
        w = s.word()
        ss = s.synset()
        lex_link = str(request.url_for('lexicon', lexicon=lex_spec))
        word_link = str(request.url_for('word', word=w.id, lexicon=lex_spec))
        synset_link = str(request.url_for('synset', synset=ss.id, lexicon=lex_spec))
        relationships: dict = {
            'word': {'links': {'related': word_link}},
            'synset': {'links': {'related': synset_link}},
            'lexicon': {'links': {'related': lex_link}}
        }
        included = []
        for relname, slist in s.relations().items():
            relationships[relname] = {
                'data': [dict(type='sense', id=_s.id) for _s in slist]
            }
            included.extend([make_sense(_s, request, basic=True) for _s in slist])
        d.update({'relationships': relationships, 'included': included})
    return d


def make_synset(ss: wn.Synset, request: Request, basic: bool = False) -> dict:
    lex_spec = ss.lexicon().specifier()
    d: dict = {
        'id': ss.id,
        'type': 'synset',
        'attributes': {
            'pos': ss.pos,
            'ili': ss._ili,
        },
        'links': {
            'self': _url_for_obj(request, 'synset', ss, lexicon=lex_spec)
        }
    }
    if not basic:
        words = ss.words()
        lex_link = str(request.url_for('lexicon', lexicon=lex_spec))
        members_link = str(request.url_for('senses', synset=ss.id, lexicon=lex_spec))
        relationships: dict = {
            'members': {'links': {'related': members_link}},
            'words': {'data': [dict(type='word', id=w.id) for w in words]},
            'lexicon': {'links': {'related': lex_link}}
        }
        included = [make_word(w, request, basic=True) for w in words]
        for relname, sslist in ss.relations().items():
            relationships[relname] = {
                'data': [dict(type='synset', id=_s.id) for _s in sslist]
            }
            included.extend([make_synset(_s, request, basic=True) for _s in sslist])
        d.update({'relationships': relationships, 'included': included})
    return d


# Route handlers

@paginate(make_lexicon)
async def lexicons(request):
    query = request.query_params
    _lexicons = wn.lexicons(
        lexicon=query.get('lexicon', '*'),
        lang=query.get('lang'),
    )
    return {'data': _lexicons}


async def lexicon(request):
    path_params = request.path_params
    lex = wn.lexicons(lexicon=path_params['lexicon'])[0]
    return JSONResponse({'data': make_lexicon(lex, request)})


def _get_words(wordnet: wn.Wordnet, request: Request) -> dict:
    query = request.query_params
    _words = wordnet.words(
        form=query.get('form'),
        pos=query.get('pos'),
    )
    return {'data': _words}


@paginate(make_word)
async def all_words(request):
    query = request.query_params
    wordnet = _init_wordnet(lexicon=query.get('lexicon'), lang=query.get('lang'))
    return _get_words(wordnet, request)


@paginate(make_word)
async def words(request):
    wordnet = _init_wordnet(request.path_params['lexicon'])
    return _get_words(wordnet, request)


async def word(request):
    path_params = request.path_params
    wordnet = _init_wordnet(request.path_params['lexicon'])
    word = wordnet.word(path_params['word'])
    return JSONResponse({'data': make_word(word, request)})


def _get_senses(wordnet: wn.Wordnet, request: Request) -> dict:
    query = request.query_params
    path = request.path_params
    if 'word' in path:
        _senses = wordnet.word(path['word']).senses()
    elif 'synset' in path:
        _senses = wordnet.synset(path['synset']).senses()
    else:
        _senses = wordnet.senses(
            form=query.get('form'),
            pos=query.get('pos'),
        )
    return {'data': _senses}


@paginate(make_sense)
async def all_senses(request):
    query = request.query_params
    wordnet = _init_wordnet(lexicon=query.get('lexicon'), lang=query.get('lang'))
    return _get_senses(wordnet, request)


@paginate(make_sense)
async def senses(request):
    wordnet = _init_wordnet(request.path_params['lexicon'])
    return _get_senses(wordnet, request)


async def sense(request):
    path_params = request.path_params
    wordnet = _init_wordnet(path_params['lexicon'])
    sense = wordnet.sense(path_params['sense'])
    return JSONResponse({'data': make_sense(sense, request)})


def _get_synsets(wordnet: wn.Wordnet, request: Request) -> dict:
    query = request.query_params
    _synsets = wordnet.synsets(
        form=query.get('form'),
        pos=query.get('pos'),
        ili=query.get('ili'),
    )
    return {'data': _synsets}


@paginate(make_synset)
async def all_synsets(request):
    query = request.query_params
    wordnet = _init_wordnet(lexicon=query.get('lexicon'), lang=query.get('lang'))
    return _get_synsets(wordnet, request)


@paginate(make_synset)
async def synsets(request):
    wordnet = _init_wordnet(request.path_params['lexicon'])
    return _get_synsets(wordnet, request)


async def synset(request):
    path_params = request.path_params
    wordnet = _init_wordnet(path_params['lexicon'])
    synset = wordnet.synset(path_params['synset'])
    return JSONResponse({'data': make_synset(synset, request)})


routes = [
    Route('/lexicons', endpoint=lexicons),
    Route('/lexicons/{lexicon}', endpoint=lexicon),
    Route('/lexicons/{lexicon}/words', endpoint=words),
    Route('/lexicons/{lexicon}/words/{word}', endpoint=word),
    Route('/lexicons/{lexicon}/words/{word}/senses', endpoint=senses),
    Route('/lexicons/{lexicon}/senses', endpoint=senses),
    Route('/lexicons/{lexicon}/senses/{sense}', endpoint=sense),
    Route('/lexicons/{lexicon}/synsets', endpoint=synsets),
    Route('/lexicons/{lexicon}/synsets/{synset}', endpoint=synset),
    Route('/lexicons/{lexicon}/synsets/{synset}/members', endpoint=senses),
    Route('/words', endpoint=all_words),
    Route('/senses', endpoint=all_senses),
    Route('/synsets', endpoint=all_synsets),
]

app = Starlette(debug=True, routes=routes)
