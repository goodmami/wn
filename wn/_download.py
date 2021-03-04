
from typing import Optional, Type
from pathlib import Path
import logging

import requests

import wn
from wn._util import is_url
from wn.util import ProgressHandler, ProgressBar
from wn._add import add as add_to_db
from wn import config


CHUNK_SIZE = 8 * 1024  # how many KB to read at a time
TIMEOUT = 10  # number of seconds to wait for a server response


logger = logging.getLogger('wn')


def download(
        project_or_url: str,
        add: bool = True,
        progress_handler: Optional[Type[ProgressHandler]] = ProgressBar,
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

    The *progress_handler* parameter takes a subclass of
    :class:`wn.util.ProgressHandler`. An instance of the class will be
    created, used, and closed by this function.

    """
    if is_url(project_or_url):
        url = project_or_url
    else:
        info = config.get_project_info(project_or_url)
        url = info['resource_url']
    logger.info('download url: %s', url)

    path = config.get_cache_path(url)
    logger.info('download cache path: %s', path)

    if progress_handler is None:
        progress_handler = ProgressHandler
    progress = progress_handler(message='Download', unit=' bytes')

    try:
        if path.exists():
            progress.flash(f'Cached file found: {path!s}')
        else:
            _download(url, path, progress)
    finally:
        progress.close()

    if add:
        try:
            add_to_db(path, progress_handler=progress_handler)
        except wn.Error as exc:
            raise wn.Error(
                f'could not add downloaded file: {path}\n  You might try '
                'deleting the cached file and trying the download again.'
            ) from exc

    return path


def _download(url: str, path: Path, progress: ProgressHandler) -> None:
    size: int = 0
    try:
        with open(path, 'wb') as f:
            progress.set(status='Requesting')
            with requests.get(url, stream=True, timeout=TIMEOUT) as response:
                size = int(response.headers.get('Content-Length', 0))
                progress.set(total=size, status='Receiving')
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                    progress.update(len(chunk))
                progress.set(status='Complete')
    except requests.exceptions.RequestException as exc:
        path.unlink()
        raise wn.Error(f'Download failed at {size} bytes') from exc
    except KeyboardInterrupt as exc:
        path.unlink()
        raise wn.Error(f'Download cancelled at {size} bytes') from exc
    except Exception:
        path.unlink()
        raise
