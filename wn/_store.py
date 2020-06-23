"""
Storage back-end interface.

The wordnets are stored in a cache directory as follows:

- index.json  : listing of added wordnets
- synsets/    : directory of project-specific synset stores
  - xyz       : synsets for the 'xyz' project
- senses/     : directory of project-specific sense stores
  - xyz       : senses for the 'xyz' project
"""


import sys
from pathlib import Path
import shelve
import json
import gzip
import hashlib
import tempfile
import shutil

import requests

from wn._types import AnyPath
from wn._exceptions import Error
from wn._util import is_gzip, progress_bar
from wn import get_project_info
from wn import _models
from wn import lmf

CHUNK_SIZE = 8 * 1024  # how many KB to read at a time

CACHE_DIRECTORY = Path.home() / '.wn_data'
DOWNLOADS_DIRECTORY = CACHE_DIRECTORY / 'downloads'
SYNSETS_DIRECTORY = CACHE_DIRECTORY / 'synsets'
SENSES_DIRECTORY = CACHE_DIRECTORY / 'senses'
INDEX_PATH = CACHE_DIRECTORY / 'index.json'

CACHE_DIRECTORY.mkdir(exist_ok=True)
DOWNLOADS_DIRECTORY.mkdir(exist_ok=True)
SYNSETS_DIRECTORY.mkdir(exist_ok=True)
SENSES_DIRECTORY.mkdir(exist_ok=True)
if not INDEX_PATH.exists():
    INDEX_PATH.write_text('{}')


def get_cache_path(url: str) -> Path:
    """Return the path for caching *url*."""
    # TODO: ETags?
    filename = hashlib.sha256(url.encode('utf-8')).hexdigest()
    return DOWNLOADS_DIRECTORY / filename


def download(project_or_url: str, version: str = None) -> None:
    """Download the wordnet specified by *project_or_url*.

    If *project_or_url* is a URL, then *version* is ignored and the
    relevant project information (code, label, version, etc.) will be
    extracted from the retrieved file. Otherwise, *project_or_url*
    must be a known project id and *version* is a known version of the
    project or is unspecified. If *version* is unspecified, the latest
    known version is retrieved.

    The retrieved file is cached locally and added to the wordnet
    database. If the URL was previously downloaded, a cached version
    will be used instead.
    """
    if '//' in project_or_url:  # assuming url must have //
        url = project_or_url
    else:
        info = get_project_info(project_or_url, version=version)
        url = info['resource_url']

    path = get_cache_path(url)
    if not path.exists():
        with open(path, 'wb') as f:
            with requests.get(url, stream=True) as response:
                size = int(response.headers.get('Content-Length', 0))
                indicator = progress_bar('Downloading ', max=size)
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                    print(indicator.send(len(chunk)), end='', file=sys.stderr)
                indicator.close()
                print(f'\r\x1b[KDownload complete ({size} bytes)', file=sys.stderr)
    add(path)


def add(source: AnyPath) -> None:
    """Add the LMF file at *source* to the database.

    The file at *source* may be gzip-compressed or plain text XML.
    """
    source = Path(source)

    if is_gzip(source):
        try:
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
                tmp_path = Path(tmp.name)
                with gzip.open(source, 'rb') as src:
                    shutil.copyfileobj(src, tmp)
            _add_lmf(tmp_path)
        finally:
            tmp_path.unlink()
    else:
        _add_lmf(source)


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
