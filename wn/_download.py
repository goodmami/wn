
import sys
from pathlib import Path
import hashlib

import requests

from wn._util import progress_bar
from wn import _store
from wn import get_project_info


CHUNK_SIZE = 8 * 1024  # how many KB to read at a time


def get_cache_path(url: str) -> Path:
    """Return the path for caching *url*."""
    # TODO: ETags?
    filename = hashlib.sha256(url.encode('utf-8')).hexdigest()
    return _store.DOWNLOADS_DIRECTORY / filename


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
        try:
            with open(path, 'wb') as f:
                with requests.get(url, stream=True) as response:
                    size = int(response.headers.get('Content-Length', 0))
                    indicator = progress_bar('Downloading ', max=size)
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                        indicator.send(len(chunk))
                    indicator.close()
                    print(f'\r\x1b[KDownload complete ({size} bytes)', file=sys.stderr)
        except:  # noqa: E722 (exception is reraised)
            print(f'\r\x1b[KDownload failed at {size} bytes', file=sys.stderr)
            path.unlink()
            raise
    _store.add(path)
