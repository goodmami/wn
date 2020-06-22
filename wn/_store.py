"""
Storage back-end interface.

The wordnets are stored in a cache directory as follows:

- index.json  : listing of added wordnets
- synsets/    : directory of project-specific synset stores
  - xyz       : synsets for the 'xyz' project
- senses/     : directory of project-specific sense stores
  - xyz       : senses for the 'xyz' project
"""


from pathlib import Path
import shelve
import json
import tempfile


from wn._types import AnyPath
from wn._exceptions import Error
from wn import _models
from wn import lmf

CACHE_DIRECTORY = Path.home() / '.wn_data'
SYNSETS_DIRECTORY = CACHE_DIRECTORY / 'synsets'
SENSES_DIRECTORY = CACHE_DIRECTORY / 'senses'
INDEX_PATH = CACHE_DIRECTORY / 'index.json'

CACHE_DIRECTORY.mkdir(exist_ok=True)
SYNSETS_DIRECTORY.mkdir(exist_ok=True)
SENSES_DIRECTORY.mkdir(exist_ok=True)
if not INDEX_PATH.exists():
    INDEX_PATH.write_text('{}')


def add(source: AnyPath) -> None:
    """Add the LMF file at *source* to the database.

    The file at *source* may be gzip-compressed or plain text XML.
    """
    source = Path(source)

    if _is_gzip(source):
        try:
            tmp_path = Path(tempfile.mkstemp(suffix='.xml'))
            with open(tmp_path, 'wb') as tmp:
                with gzip.open(source, 'rb') as src:
                    shutil.copyfileobj(src, tmp)
            _add_lmf(tmp_path)
        finally:
            tmp_path.unlink()
    else:
        _add_lmf(source)


def _is_gzip(path: Path) -> bool:
    """Return True if the file at *path* appears to be gzipped."""
    with path.open('rb') as f:
        return f.read(2) == b'\x1F\x8B'


def _add_lmf(source):
    lexicons = lmf.load(source)
    for lexicon in lexicons:
        key = f'{lexicon.id}-{lexicon.version}'
        with INDEX_PATH.open() as f:
            index = json.load(f)
        if key in index:
            raise Error(f'wordnet already added: {key}')
        synset_sense_map = {}
        sense_count = 0
        with shelve.open(str(SENSES_DIRECTORY / key)) as db:
            for entry in lexicon.lexical_entries:
                for sense in entry.senses:
                    db[sense.id] = _models.Sense(
                        sense.id,
                        sense.synset,
                        entry.lemma.form,
                        entry.lemma.pos,
                        entry.lemma.script,
                        {rel.type: rel.target for rel in sense.relations},
                        tuple(ex.text for ex in sense.examples))
                    synset_sense_map.setdefault(sense.synset, []).append(sense.id)
                    sense_count += 1
        with shelve.open(str(SYNSETS_DIRECTORY / key)) as db:
            for synset in lexicon.synsets:
                db[synset.id] = _models.Synset(
                    synset.id,
                    synset.ili,
                    synset.pos,
                    tuple(defn.text for defn in synset.definitions),
                    {rel.type: rel.target for rel in synset.relations},
                    tuple(ex.text for ex in synset.examples),
                    tuple(synset_sense_map.get(synset.id, ())))
        index[key] = {
            'id': lexicon.id,
            'version': lexicon.version,
            'label': lexicon.label,
            'language': lexicon.language,
            'email': lexicon.email,
            'url': lexicon.url,
            'sense_count': sense_count,
            'synset_count': len(lexicon.synsets),
        }
        with INDEX_PATH.open('w') as f:
            json.dump(index, f)


def get_synset(id: str, key: str) -> _models.Synset:
    with shelve.open(str(SYNSETS_DIRECTORY / key)) as db:
        return db[id]


def get_sense(id: str, key: str) -> _models.Sense:
    with shelve.open(str(SENSES_DIRECTORY / key)) as db:
        return db[id]
