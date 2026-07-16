"""Web interface for Wn databases."""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache, wraps
from urllib.parse import parse_qs, urlencode, urlsplit

from starlette.applications import Starlette  # type: ignore
from starlette.exceptions import HTTPException  # type: ignore
from starlette.middleware import Middleware  # type: ignore
from starlette.middleware.cors import CORSMiddleware  # type: ignore
from starlette.middleware.gzip import GZipMiddleware  # type: ignore
from starlette.requests import Request  # type: ignore
from starlette.responses import JSONResponse  # type: ignore
from starlette.routing import Route  # type: ignore

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
            last = (total // limit) * limit

            obj['data'] = [proto(x, request) for x in obj['data'][offset:next]]
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


def cached_response(months: float):
    """Decorator to add Cache-Control header to responses."""

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request):
            response: JSONResponse = await func(request)
            if not isinstance(response, JSONResponse):
                response = JSONResponse(response)

            seconds = int(months * 30 * 24 * 60 * 60)
            response.headers['Cache-Control'] = f'public, max-age={seconds}'
            return response

        return wrapper

    return decorator

def replace_query_params(url: str, **params) -> str:
    u = urlsplit(url)
    q = parse_qs(u.query)
    q.update(params)
    qs = urlencode(q, doseq=True)
    return u._replace(query=qs).geturl()


# Wordnet-instantiation

def _init_wordnet(
        lexicon: str = '*',
        lang: str | None = None,
) -> wn.Wordnet:
    if lexicon == '*' and lang is not None:
        lexicon = ' '.join(lex.specifier() for lex in wn.lexicons(lang=lang))
    return wn.Wordnet(lexicon)


# Data-making functions

def _make_pronunciation_data(p: wn.Pronunciation) -> dict:
    d: dict = {'value': p.value, 'phonemic': p.phonemic}
    if p.variety:
        d['variety'] = p.variety
    if p.notation:
        d['notation'] = p.notation
    if p.audio:
        d['audio'] = p.audio
    return d


def _make_form_data(f: wn.Form) -> dict:
    d: dict = {'form': f.value}
    if f.script:
        d['script'] = f.script
    pronunciations = f.pronunciations()
    if pronunciations:
        d['pronunciations'] = [_make_pronunciation_data(p) for p in pronunciations]
    return d

def _url_for_obj(
        request: Request,
        name: str,
        obj: wn.Word | wn.Sense | wn.Synset,
        lexicon: str | None = None,
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


def _make_synset_link(ss: wn.Synset) -> dict:
    lemmas = ss.lemmas()
    return {'id': ss.id, 'lemma': lemmas[0] if lemmas else None}


# Synset relations inlined into the word response as `related` so the
# dictionary word page can render "see also" links without fetching each
# synset's relationship graph separately.
INLINE_WORD_RELATIONS = ('similar', 'also')


def make_word(w: wn.Word, request: Request, basic: bool = False) -> dict:
    lex_spec = w.lexicon().specifier()
    d: dict = {
        'id': w.id,
        'type': 'word',
        'attributes': {
            'pos': w.pos,
            'lemma': w.lemma(),
            'forms': [_make_form_data(f) for f in w.forms(data=True)],
        },
        'links': {
            'self': _url_for_obj(request, 'word', w, lexicon=lex_spec)
        }
    }
    if not basic:
        synsets = w.synsets()
        lex_link = str(request.url_for('lexicon', lexicon=lex_spec))
        senses_link = str(request.url_for('senses', word=w.id, lexicon=lex_spec))

        sense_counts = {s.synset().id: sum(s.counts()) for s in w.senses()}
        included = []
        for ss in synsets:
            ss_data = make_synset(ss, request, basic=True)
            attrs = ss_data['attributes']
            attrs['count'] = sense_counts.get(ss.id, 0)
            attrs['members'] = ss.lemmas()
            paths = ss.hypernym_paths()
            if paths:
                # First (usually only) path, reordered root -> immediate
                # hypernym, ready to render as a breadcrumb.
                attrs['hypernyms'] = [
                    _make_synset_link(hss) for hss in reversed(paths[0])
                ]
            related = {
                relname: [_make_synset_link(rss) for rss in sslist]
                for relname, sslist in ss.relations(*INLINE_WORD_RELATIONS).items()
            }
            if related:
                attrs['related'] = related
            included.append(ss_data)

        d.update({
            'relationships': {
                'senses': {'links': {'related': senses_link}},
                'synsets': {
                    'data': [{'type': 'synset', 'id': ss.id} for ss in synsets],
                },
                'lexicon': {'links': {'related': lex_link}}
            },
            'included': included
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
                'data': [{'type': 'sense', 'id': _s.id} for _s in slist]
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
            'definition': ss.definition(),
            'examples': ss.examples(),
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
            'words': {'data': [{'type': 'word', 'id': w.id} for w in words]},
            'lexicon': {'links': {'related': lex_link}}
        }
        included = [make_word(w, request, basic=True) for w in words]
        for relname, sslist in ss.relations().items():
            relationships[relname] = {
                'data': [{'type': 'synset', 'id': _s.id} for _s in sslist]
            }
            included.extend([make_synset(_s, request, basic=True) for _s in sslist])
        d.update({'relationships': relationships, 'included': included})
    return d


# Exception handlers

async def http_exception_handler(request: Request, exc: Exception):
    status_code = exc.status_code if hasattr(exc, 'status_code') else 500
    return JSONResponse({
        "error": {
            "status": status_code,
            "message": exc.detail if hasattr(exc, 'detail') else str(exc),
            "type": type(exc).__name__
        }
    }, status_code=status_code)


# Route handlers

@cached_response(months=1)
@paginate(make_lexicon)
async def lexicons(request):
    query = request.query_params
    _lexicons = wn.lexicons(
        lexicon=query.get('lexicon', '*'),
        lang=query.get('lang'),
    )
    return {'data': _lexicons}


@cached_response(months=1)
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


@cached_response(months=1)
@paginate(make_word)
async def all_words(request):
    query = request.query_params
    wordnet = _init_wordnet(lexicon=query.get('lexicon'), lang=query.get('lang'))
    return _get_words(wordnet, request)


@cached_response(months=1)
@paginate(make_word)
async def words(request):
    wordnet = _init_wordnet(request.path_params['lexicon'])
    return _get_words(wordnet, request)


@lru_cache(maxsize=10)
def _get_forms(lexicon: str, with_entities: bool = True):
    from wn._db import connect

    conn = connect()

    # Parse lexicon specifier (format: "id:version")
    parts = lexicon.split(':', 1)
    if len(parts) != 2:
        return []
    lex_id, lex_version = parts

    # Optimized query using indexed columns and SQL DISTINCT
    # Direct join from forms to lexicons using the new index on forms.lexicon_rowid
    query = '''
        SELECT DISTINCT f.form
          FROM forms AS f
          JOIN lexicons AS lex ON lex.rowid = f.lexicon_rowid
         WHERE lex.id = ? AND lex.version = ?
    '''
    if not with_entities:
        query += ' AND f.form = LOWER(f.form)'

    rows = conn.execute(query, (lex_id, lex_version)).fetchall()

    return [row[0] for row in rows]


@cached_response(months=1)
async def forms(request):
    lexicon = request.path_params['lexicon']
    with_entities = request.query_params.get('with_entities', 'true').lower() != 'false'
    print(f"forms: got request lexicon={lexicon} with_entities={with_entities}")

    print("forms: getting forms")
    forms = _get_forms(lexicon, with_entities=with_entities)
    print(f"forms: got {len(forms)} forms")

    print("forms: constructing JSON response")
    response = JSONResponse(content={
        "data": forms,
        "meta": {"total": len(forms)}
    })
    print("forms: finished")
    return response


@cached_response(months=1)
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


@cached_response(months=1)
@paginate(make_sense)
async def all_senses(request):
    query = request.query_params
    wordnet = _init_wordnet(lexicon=query.get('lexicon'), lang=query.get('lang'))
    return _get_senses(wordnet, request)


@cached_response(months=1)
@paginate(make_sense)
async def senses(request):
    wordnet = _init_wordnet(request.path_params['lexicon'])
    return _get_senses(wordnet, request)


@cached_response(months=1)
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


@cached_response(months=1)
@paginate(make_synset)
async def all_synsets(request):
    query = request.query_params
    wordnet = _init_wordnet(lexicon=query.get('lexicon'), lang=query.get('lang'))
    return _get_synsets(wordnet, request)


@cached_response(months=1)
@paginate(make_synset)
async def synsets(request):
    wordnet = _init_wordnet(request.path_params['lexicon'])
    return _get_synsets(wordnet, request)


@cached_response(months=1)
async def synset(request):
    path_params = request.path_params
    wordnet = _init_wordnet(path_params['lexicon'])
    synset = wordnet.synset(path_params['synset'])
    return JSONResponse({'data': make_synset(synset, request)})


async def index(request: Request):
    endpoints = {route.path: str(request.url_for(route.name))
                 for route in routes if len(route.param_convertors) == 0}
    return JSONResponse({'endpoints': endpoints})


async def health_check(request: Request):
    body = {
        'status': 'healthy',
        'timestamp': datetime.now(tz=UTC).isoformat(),
        'service': 'wn.web',
    }
    return JSONResponse(body, status_code=200)


async def definitions(request: Request):
    """Batch endpoint to get definitions for multiple word form/pos queries.

    POST body: {"queries": [{"form": "comfort", "pos": "n"}, ...]}
    Response: {"data": [{"form": "comfort", "pos": "n",
                         "definitions": {synset_id: def, ...}}, ...]}
    """
    path_params = request.path_params
    wordnet = _init_wordnet(path_params['lexicon'])

    body = await request.json()
    queries = body.get('queries', [])

    results = []
    for query in queries:
        form = query.get('form')
        pos = query.get('pos')

        # Get all synsets for this form/pos combination
        synsets = wordnet.synsets(form=form, pos=pos)

        # Build synset_id -> definition mapping
        definitions_map = {
            ss.id: ss.definition()
            for ss in synsets
            if ss.definition()  # Only include if definition exists
        }

        results.append({
            'form': form,
            'pos': pos,
            'definitions': definitions_map
        })

    return JSONResponse({'data': results})


routes = [
    Route('/', endpoint=index),
    Route('/health', endpoint=health_check),
    Route('/lexicons', endpoint=lexicons),
    Route('/lexicons/{lexicon}', endpoint=lexicon),
    Route('/lexicons/{lexicon}/forms', endpoint=forms),
    Route('/lexicons/{lexicon}/words', endpoint=words),
    Route('/lexicons/{lexicon}/words/{word}', endpoint=word),
    Route('/lexicons/{lexicon}/words/{word}/senses', endpoint=senses),
    Route('/lexicons/{lexicon}/senses', endpoint=senses),
    Route('/lexicons/{lexicon}/senses/{sense}', endpoint=sense),
    Route('/lexicons/{lexicon}/synsets', endpoint=synsets),
    Route('/lexicons/{lexicon}/synsets/{synset}', endpoint=synset),
    Route('/lexicons/{lexicon}/synsets/{synset}/members', endpoint=senses),
    Route('/lexicons/{lexicon}/definitions', endpoint=definitions, methods=['POST']),
    Route('/words', endpoint=all_words),
    Route('/senses', endpoint=all_senses),
    Route('/synsets', endpoint=all_synsets),
]

middlewares = [
    # Level 4: best size/speed tradeoff (29% ratio @ 23ms vs 28% @ 268ms for level 9)
    Middleware(GZipMiddleware, minimum_size=1000, compresslevel=4),
    Middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_methods=['*'],
        allow_headers=['*'],
    )
]

@asynccontextmanager
async def lifespan(app):
    lexicons = wn.lexicons()
    if lexicons:
        _get_forms(lexicons[0].specifier())
    yield


app = Starlette(debug=True,
                routes=routes,
                middleware=middlewares,
                lifespan=lifespan,
                exception_handlers={
                    HTTPException: http_exception_handler,
                    wn.Error: http_exception_handler,
                    Exception: http_exception_handler,
                })
