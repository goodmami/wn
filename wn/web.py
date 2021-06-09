
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
    return request.url_for(name, **kwargs)


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
            'self': request.url_for('lexicon', lexicon=spec)
        },
        'relationships': {
            'words': {
                'links': {'related': request.url_for('words', lexicon=spec)},
            },
            'synsets': {
                'links': {'related': request.url_for('synsets', lexicon=spec)},
            },
            'senses': {
                'links': {'related': request.url_for('senses', lexicon=spec)},
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
        lex_link = request.url_for('lexicon', lexicon=lex_spec)
        senses_link = request.url_for('senses', word=w.id, lexicon=lex_spec)
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
        lex_link = request.url_for('lexicon', lexicon=lex_spec)
        word_link = request.url_for('word', word=w.id, lexicon=lex_spec)
        synset_link = request.url_for('synset', synset=ss.id, lexicon=lex_spec)
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
        lex_link = request.url_for('lexicon', lexicon=lex_spec)
        members_link = request.url_for('senses', synset=ss.id, lexicon=lex_spec)
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


@paginate(make_lexicon)
async def lexicons(request):
    query = request.query_params
    _lexicons = wn.lexicons(
        lexicon=query.get('lexicon'),
        lang=query.get('lang'),
    )
    return {'data': _lexicons}


async def lexicon(request):
    path_params = request.path_params
    lex = wn.lexicons(lexicon=path_params['lexicon'])[0]
    return JSONResponse({'data': make_lexicon(lex, request)})


@paginate(make_word)
async def words(request):
    query = request.query_params
    lexicon = request.path_params.get('lexicon') or query.get('lexicon')
    _words = wn.words(
        form=query.get('form'),
        pos=query.get('pos'),
        lexicon=lexicon,
        lang=query.get('lang'),
    )
    return {'data': _words}


async def word(request):
    path_params = request.path_params
    word = wn.word(path_params['word'], lexicon=path_params['lexicon'])
    return JSONResponse({'data': make_word(word, request)})


@paginate(make_sense)
async def senses(request):
    query = request.query_params
    path = request.path_params
    lexicon = path.get('lexicon') or query.get('lexicon')
    if 'word' in path:
        _senses = wn.word(path['word'], lexicon=lexicon).senses()
    elif 'synset' in path:
        _senses = wn.synset(path['synset'], lexicon=lexicon).members()
    else:
        _senses = wn.senses(
            form=query.get('form'),
            pos=query.get('pos'),
            lexicon=lexicon,
            lang=query.get('lang'),
        )
    return {'data': _senses}


async def sense(request):
    path_params = request.path_params
    sense = wn.sense(path_params['sense'], lexicon=path_params['lexicon'])
    return JSONResponse({'data': make_sense(sense, request)})


@paginate(make_synset)
async def synsets(request):
    query = request.query_params
    lexicon = request.path_params.get('lexicon') or query.get('lexicon')
    _synsets = wn.synsets(
        form=query.get('form'),
        pos=query.get('pos'),
        ili=query.get('ili'),
        lexicon=lexicon,
        lang=query.get('lang'),
    )
    return {'data': _synsets}


async def synset(request):
    path_params = request.path_params
    synset = wn.synset(path_params['synset'], lexicon=path_params['lexicon'])
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
    Route('/words', endpoint=words),
    Route('/senses', endpoint=senses),
    Route('/synsets', endpoint=synsets),
]

app = Starlette(debug=True, routes=routes)
