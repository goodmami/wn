
from functools import wraps

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

import wn

DEFAULT_PAGINATION_LIMIT = 50


def paginate(name, proto):

    def paginate_wrapper(func):

        @wraps(func)
        async def _paginate_wrapper(request):
            query = request.query_params
            offset = abs(int(query.get('offset', 0)))
            limit = abs(int(query.get('limit', DEFAULT_PAGINATION_LIMIT)))

            obj = await func(request)

            seq = obj[name]
            obj[name] = [proto(x, request) for x in seq[offset:offset+limit]]
            obj['offset'] = offset
            obj['limit'] = limit
            obj['total'] = len(seq)

            return JSONResponse(obj)

        return _paginate_wrapper

    return paginate_wrapper


# Data-making functions

def make_lexicon(lex, request):
    return {
        'id': lex.id,
        'version': lex.version,
        'label': lex.label,
        'language': lex.language,
        'license': lex.license,
        'synsets': request.url_for('synsets', lexicon=lex.specifier()),
    }


def make_word(w, request):
    return {
        'id': w.id,
        'pos': w.pos,
        'lemma': w.lemma(),
        'forms': w.forms(),
        'senses': [
            request.url_for('sense', lexicon=s.lexicon().specifier(), sense=s.id)
            for s in w.senses()
        ],
        'lexicon': request.url_for(
            'lexicons', lexicon=w.lexicon().specifier()
        ),
    }


def make_sense(s, request):
    word = s.word()
    synset = s.synset()
    return {
        'id': s.id,
        'word': request.url_for(
            'word', lexicon=word.lexicon().specifier(), word=word.id
        ),
        'synset': request.url_for(
            'synset', lexicon=synset.lexicon().specifier(), synset=synset.id
        ),
        'lexicon': request.url_for(
            'lexicons', lexicon=s.lexicon().specifier()
        ),
    }


def make_synset(ss, request):
    return {
        'id': ss.id,
        'pos': ss.pos,
        'ili': ss._ili,
        'members': [
            request.url_for('sense', lexicon=s.lexicon().specifier(), sense=s.id)
            for s in ss.senses()
        ],
        # 'relations': [],
        'lexicon': request.url_for(
            'lexicons', lexicon=ss.lexicon().specifier()
        ),
    }


@paginate('lexicons', make_lexicon)
async def lexicons(request):
    query = request.query_params
    lexicon = request.path_params.get('lexicon') or query.get('lexicon')
    _lexicons = wn.lexicons(
        lexicon=lexicon,
        lang=query.get('lang'),
    )
    return {'lexicons': _lexicons}


@paginate('words', make_word)
async def words(request):
    query = request.query_params
    lexicon = request.path_params.get('lexicon') or query.get('lexicon')
    _words = wn.words(
        form=query.get('form'),
        pos=query.get('pos'),
        lexicon=lexicon,
        lang=query.get('lang'),
    )
    return {'words': _words}


async def word(request):
    path_params = request.path_params
    word = wn.word(path_params['word'], lexicon=path_params['lexicon'])
    return JSONResponse({'word': make_word(word, request)})


@paginate('senses', make_sense)
async def senses(request):
    query = request.query_params
    lexicon = request.path_params.get('lexicon') or query.get('lexicon')
    _senses = wn.senses(
        form=query.get('form'),
        pos=query.get('pos'),
        lexicon=lexicon,
        lang=query.get('lang'),
    )
    return {'senses': _senses}


async def sense(request):
    path_params = request.path_params
    sense = wn.sense(path_params['sense'], lexicon=path_params['lexicon'])
    return JSONResponse({'sense': make_sense(sense, request)})


@paginate('synsets', make_synset)
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
    return {'synsets': _synsets}


async def synset(request):
    path_params = request.path_params
    synset = wn.synset(path_params['synset'], lexicon=path_params['lexicon'])
    return JSONResponse({'synset': make_synset(synset, request)})


routes = [
    Route('/lexicons', endpoint=lexicons),
    Route('/lexicons/{lexicon}', endpoint=lexicons),
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
