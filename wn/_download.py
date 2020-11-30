
import sys

import requests

from wn._util import ProgressBar, is_url
from wn import _db
from wn import config


CHUNK_SIZE = 8 * 1024  # how many KB to read at a time
TIMEOUT = 10  # number of seconds to wait for a server response


def download(project_or_url: str) -> None:
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
    Download complete (13643357 bytes)
    Checking /tmp/tmp_uqntl0l.xml
    Reading /tmp/tmp_uqntl0l.xml
    Building [###############################] (1337590/1337590)

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
        try:
            with open(path, 'wb') as f:
                with requests.get(url, stream=True, timeout=TIMEOUT) as response:
                    size = int(response.headers.get('Content-Length', 0))
                    indicator = ProgressBar('Downloading ', max=size)
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                        indicator.update(len(chunk))
                    print(f'\r\x1b[KDownload complete ({size} bytes)', file=sys.stderr)
        except:  # noqa: E722 (exception is reraised)
            print(f'\r\x1b[KDownload failed at {size} bytes', file=sys.stderr)
            path.unlink()
            raise
    _db.add(path)
