
from collections.abc import Sequence
from typing import Optional
from pathlib import Path
import logging

import httpx

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
        progress_handler: Optional[type[ProgressHandler]] = ProgressBar,
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
    if progress_handler is None:
        progress_handler = ProgressHandler
    progress = progress_handler(message='Download', unit=' bytes')

    cache_path, urls = _get_cache_path_and_urls(project_or_url)

    try:
        if cache_path and cache_path.exists():
            progress.flash(f'Cached file found: {cache_path!s}')
            path = cache_path
        elif urls:
            path = _download(urls, progress)
        else:
            raise wn.Error('no urls to download')
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


def _get_cache_path_and_urls(project_or_url: str) -> tuple[Optional[Path], list[str]]:
    if is_url(project_or_url):
        return config.get_cache_path(project_or_url), [project_or_url]
    else:
        info = config.get_project_info(project_or_url)
        return info.get('cache'), info['resource_urls']


def _download(urls: Sequence[str], progress: ProgressHandler) -> Path:
    client = httpx.Client(timeout=TIMEOUT, follow_redirects=True)
    try:
        for i, url in enumerate(urls, 1):
            path = config.get_cache_path(url)
            logger.info('download url: %s', url)
            logger.info('download cache path: %s', path)
            try:
                with open(path, 'wb') as f:
                    progress.set(status='Requesting', count=0)
                    with client.stream("GET", url) as response:
                        response.raise_for_status()
                        total = int(response.headers.get('Content-Length', 0))
                        count = response.num_bytes_downloaded
                        progress.set(count=count, total=total, status='Receiving')
                        for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                            progress.update(response.num_bytes_downloaded - count)
                            count = response.num_bytes_downloaded
                        progress.set(status='Complete')
            except httpx.RequestError as exc:
                path.unlink(missing_ok=True)
                last_count = progress.kwargs['count']
                if i == len(urls):
                    raise wn.Error(f'download failed at {last_count} bytes') from exc
                else:
                    logger.info(
                        'download failed at %d bytes; trying next url', last_count
                    )
            else:
                break  # success

    except KeyboardInterrupt as exc:
        path.unlink(missing_ok=True)
        last_count = progress.kwargs['count']
        raise wn.Error(f'download cancelled at {last_count} bytes') from exc
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        client.close()

    return path
