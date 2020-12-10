
import sys

import requests

from wn._util import get_progress_handler, is_url
from wn import _db
from wn import config


CHUNK_SIZE = 8 * 1024  # how many KB to read at a time
TIMEOUT = 10  # number of seconds to wait for a server response


def download(project_or_url: str, progress_handler=get_progress_handler) -> None:
    """Download the wordnet specified by *project_or_url*.

    If *project_or_url* starts with `'http://'` or `'https://'`, then
    it is taken to be a URL and the relevant project information
    (code, label, version, etc.) will be extracted from the retrieved
    file. Otherwise, *project_or_url* must be a known project id,
    optionally followed by `':'` and a known version. If the version
    is unspecified, the latest known version is retrieved.

    The retrieved file is cached locally and added to the wordnet
    database. If the URL was previously downloaded, a cached version
    will be used instead.

    >>> wn.download('ewn:2020')
    Added ewn:2020 (English WordNet)

    The *progress_handler* parameter takes a callable that is called
    after every chunk of bytes is received. The handler function
    should have the following signature:

    .. code-block:: python

       def progress_handler(n: int, **kwargs) -> str:
           ...

    The *n* parameter is the number of bytes received in a chunk. When
    a request is sent, the handler function is called with ``max`` key
    in *kwargs* mapped to the total number of bytes (taken from the
    response's ``Content-Length`` header). A ``status`` key may also
    indicate the current status (``Requesting``, ``Receiving``,
    ``Completed``).

    """
    if is_url(project_or_url):
        url = project_or_url
    else:
        info = config.get_project_info(project_or_url)
        url = info['resource_url']

    path = config.get_cache_path(url)

    if path.exists():
        print(f'Cached file found: {path!s}', file=sys.stderr)

    else:
        callback = get_progress_handler(progress_handler, 'Download', 'bytes', '')
        size: int = 0
        try:
            with open(path, 'wb') as f:
                callback(0, status='Requesting')
                with requests.get(url, stream=True, timeout=TIMEOUT) as response:
                    size = int(response.headers.get('Content-Length', 0))
                    callback(0, max=size, status='Receiving')
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                        callback(len(chunk))
                    callback(0, status='Complete')
        except:  # noqa: E722 (exception is reraised)
            print(f'\r\x1b[KDownload failed at {size} bytes', file=sys.stderr)
            path.unlink()
            raise
    _db.add(path)
