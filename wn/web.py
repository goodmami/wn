
from functools import wraps
from urllib.parse import urlsplit, parse_qs, urlencode

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import wn

DEFAULT_PAGINATION_LIMIT = 50


def paginate(proto):

    def paginate_wrapper(func):

        @wraps(func)
        async def _paginate_wrapper(request):
            url = str(request.url)
            query = dict(request.query_params)
            offset = abs(int(query.pop('offset', 0)))
            limit = abs(int(query.pop('limit', DEFAULT_PAGINATION_LIMIT)))

            obj = await func(request)
            total = len(obj['data'])

            links = {
                'first': replace_query_params(url, offset=0),
                'last': replace_query_params(url, offset=(total//limit)*limit),
                'prev': replace_query_params(url, offset=max(0, offset - limit)),
                'next': replace_query_params(url, offset=offset + limit),
            }
            obj['data'] = [proto(x, request)
                           for x in obj['data'][offset:offset+limit]]
            obj.setdefault('meta', {}).update(total=total)
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

def _url_for_obj(request, name, obj, lexicon=None):
    if lexicon is None:
        lexicon = obj.lexicon().specifier()
    kwargs = {
        'lexicon': lexicon,
        name: obj.id
    }
    return request.url_for(name, **kwargs)


def make_lexicon(lex, request):
    spec = lex.specifier()
    return {
        'id': lex.id,
        'type': 'lexicon',
        'attributes': {
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


def make_word(w, request):
    lex_spec = w.lexicon().specifier()
    senses = w.senses()
    synsets = w.synsets()
    return {
        'id': w.id,
        'type': 'word',
        'attributes': {
            'pos': w.pos,
            'lemma': w.lemma(),
            'forms': w.forms(),
        },
        'links': {
            'self': _url_for_obj(request, 'word', w, lexicon=lex_spec)
        },
        'relationships': {
            'senses': {'data': [{'type': 'sense', 'id': s.id} for s in senses]},
            'synsets': {'data': [{'type': 'synset', 'id': ss.id} for ss in synsets]},
            'lexicon': {
                'links': {'related': request.url_for('lexicon', lexicon=lex_spec)}
            }
        },
        'included': [
            {'type': 'sense',
             'id': s.id,
             'links': {'self': _url_for_obj(request, 'sense', s)}}
            for s in senses
        ] + [
            {'type': 'synset',
             'id': ss.id,
             'links': {'self': _url_for_obj(request, 'synset', ss)}}
            for ss in synsets
        ]
    }


def make_sense(s, request):
    lex_spec = s.lexicon().specifier()
    w = s.word()
    ss = s.synset()
    return {
        'id': s.id,
        'type': 'sense',
        'links': {
            'self': _url_for_obj(request, 'sense', s, lexicon=lex_spec)
        },
        'relationships': {
            'word': {'data': {'type': 'word', 'id': w.id}},
            'synset': {'data': {'type': 'synset', 'id': ss.id}},
            'lexicon': {
                'links': {'related': request.url_for('lexicon', lexicon=lex_spec)}
            }
        },
        'included': [
            {'type': 'word',
             'id': w.id,
             'attributes': {
                'pos': w.pos,
                'lemma': w.lemma(),
                'forms': w.forms(),
             },
             'links': {'self': _url_for_obj(request, 'word', w)}},
            {'type': 'synset',
             'id': ss.id,
             'links': {'self': _url_for_obj(request, 'synset', ss)}}
        ]
    }


def make_synset(ss, request):
    lex_spec = ss.lexicon().specifier()
    senses = ss.senses()
    words = ss.words()
    return {
        'id': ss.id,
        'type': 'synset',
        'attributes': {
            'pos': ss.pos,
            'ili': ss._ili,
        },
        'links': {
            'self': _url_for_obj(request, 'synset', ss, lexicon=lex_spec)
        },
        'relationships': {
            'members': {'data': [{'type': 'sense', 'id': s.id} for s in senses]},
            'words': {'data': [{'type': 'word', 'id': w.id} for w in words]},
            'lexicon': {
                'links': {'related': request.url_for('lexicon', lexicon=lex_spec)}
            }
        },
        'included': [
            {'type': 'sense',
             'id': s.id,
             'links': {'self': _url_for_obj(request, 'sense', s)}}
            for s in senses
        ] + [
            {'type': 'word',
             'id': w.id,
             'links': {'self': _url_for_obj(request, 'word', w)}}
            for w in words
        ]
    }


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
    return JSONResponse({'word': make_word(word, request)})


@paginate(make_sense)
async def senses(request):
    query = request.query_params
    lexicon = request.path_params.get('lexicon') or query.get('lexicon')
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
    return JSONResponse({'sense': make_sense(sense, request)})


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
    return JSONResponse({'synset': make_synset(synset, request)})


routes = [
    Route('/lexicons', endpoint=lexicons),
    Route('/lexicons/{lexicon}', endpoint=lexicon),
    Route('/lexicons/{lexicon}/words', endpoint=words),
    Route('/lexicons/{lexicon}/words/{word}', endpoint=word),
    Route('/lexicons/{lexicon}/senses', endpoint=senses),
    Route('/lexicons/{lexicon}/senses/{sense}', endpoint=sense),
    Route('/lexicons/{lexicon}/synsets', endpoint=synsets),
    Route('/lexicons/{lexicon}/synsets/{synset}', endpoint=synset),
    Route('/words', endpoint=words),
    Route('/senses', endpoint=senses),
    Route('/synsets', endpoint=synsets),
]

app = Starlette(debug=True, routes=routes)
