
from typing import Callable, Optional
import sys
from pathlib import Path

import requests

import wn
from wn._util import get_progress_handler, is_url
from wn import _db
from wn import config


CHUNK_SIZE = 8 * 1024  # how many KB to read at a time
TIMEOUT = 10  # number of seconds to wait for a server response


def download(
        project_or_url: str,
        add: bool = True,
        progress_handler: Optional[Callable] = get_progress_handler,
) -> Path:
    """Download the resource specified by *project_or_url*.

    First the URL of the resource is determined and then, depending on
    the parameters, the resource is downloaded and added to the
    database.  The function then returns the path of the cached file.

    If *project_or_url* starts with `'http://'` or `'https://'`, then
    it is taken to be the URL for the resource. Otherwise,
    *project_or_url* is taken as a :ref:`project specifier
    <lexicon-specifiers>` and the URL is taken from a matching entry
    in Wn's project index. If no project matches the specifier,
    :exc:`wn.Error` is raised.

    If the URL has been downloaded and cached before, the cached file
    is used. Otherwise the URL is retrieved and stored in the cache.

    If the *add* paramter is ``True`` (default), the downloaded
    resource is added to the database.

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
        size: int = 0
        try:
            callback = get_progress_handler(progress_handler, 'Download', 'bytes', '')
            callback(0, count=0, max=0, status='Initializing')
            with open(path, 'wb') as f:
                callback(0, status='Requesting')
                with requests.get(url, stream=True, timeout=TIMEOUT) as response:
                    size = int(response.headers.get('Content-Length', 0))
                    callback(0, max=size, status='Receiving')
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                        callback(len(chunk))
                    callback(0, status='Complete\n')
        except (Exception, KeyboardInterrupt) as exc:
            path.unlink()
            raise wn.Error(f'Download failed at {size} bytes') from exc

    if add:
        _db.add(path, progress_handler=progress_handler)

    return path
