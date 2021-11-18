
"""
Local configuration settings.
"""

from typing import Optional, Dict, Sequence, Any
from pathlib import Path

import tomli

from wn import ConfigurationError, ProjectError
from wn._types import AnyPath
from wn.constants import _WORDNET
from wn._util import resources, short_hash

# The directory where downloaded and added data will be stored.
DEFAULT_DATA_DIRECTORY = Path.home() / '.wn_data'
DATABASE_FILENAME = 'wn.db'


class WNConfig:

    def __init__(self):
        self._data_directory = DEFAULT_DATA_DIRECTORY
        self._projects = {}
        self._dbpath = self._data_directory / DATABASE_FILENAME
        self.allow_multithreading = False

    @property
    def data_directory(self) -> Path:
        """The file system directory where Wn's data is stored."""
        dir = self._data_directory
        dir.mkdir(exist_ok=True)
        return dir

    @data_directory.setter
    def data_directory(self, path):
        dir = Path(path).expanduser()
        if dir.exists() and not dir.is_dir():
            raise ConfigurationError(f'path exists and is not a directory: {dir}')
        self._data_directory = dir
        self._dbpath = dir / DATABASE_FILENAME

    @property
    def database_path(self):
        """The path to the database file."""
        return self._dbpath

    @property
    def downloads_directory(self):
        """The file system directory where downloads are cached."""
        dir = self.data_directory / 'downloads'
        dir.mkdir(exist_ok=True)
        return dir

    @property
    def index(self) -> Dict[str, Dict]:
        """The project index."""
        return self._projects

    def add_project(
        self,
        id: str,
        type: str = _WORDNET,
        label: str = None,
        language: str = None,
        license: str = None,
        error: str = None,
    ) -> None:
        """Add a new wordnet project to the index.

        Arguments:
            id: short identifier of the project
            type: project type (default 'wordnet')
            label: full name of the project
            language: `BCP 47`_ language code of the resource
            license: link or name of the project's default license
            error: if set, the error message to use when the project
              is accessed

        .. _BCP 47: https://en.wikipedia.org/wiki/IETF_language_tag
        """
        if id in self._projects:
            raise ValueError(f'project already added: {id}')
        self._projects[id] = {
            'type': type,
            'label': label,
            'language': language,
            'versions': {},
            'license': license,
        }
        if error:
            self._projects[id]['error'] = error

    def add_project_version(
        self,
        id: str,
        version: str,
        url: str = None,
        error: str = None,
        license: str = None,
    ) -> None:
        """Add a new resource version for a project.

        Exactly one of *url* or *error* must be specified.

        Arguments:
            id: short identifier of the project
            version: version string of the resource
            url: space-separated list of web addresses for the resource
            license: link or name of the resource's license; if not
              given, the project's default license will be used.
            error: if set, the error message to use when the project
              is accessed

        """
        version_data: Dict[str, Any]
        if url and not error:
            version_data = {'resource_urls': url.split()}
        elif error and not url:
            version_data = {'error': error}
        elif url and error:
            raise ConfigurationError(f'{id}:{version} specifies both url and redirect')
        else:
            version_data = {}
        if license:
            version_data['license'] = license
        project = self._projects[id]
        project['versions'][version] = version_data

    def get_project_info(self, arg: str) -> Dict:
        """Return information about an indexed project version.

        If the project has been downloaded and cached, the ``"cache"``
        key will point to the path of the cached file, otherwise its
        value is ``None``.

        Arguments:
            arg: a project specifier

        Example:

            >>> info = wn.config.get_project_info('oewn:2021')
            >>> info['label']
            'Open English WordNet'

        """
        id, _, version = arg.partition(':')
        if id not in self._projects:
            raise ProjectError(f'no such project id: {id}')
        project: Dict = self._projects[id]
        if 'error' in project:
            raise ProjectError(project['error'])

        versions: Dict = project['versions']
        if not version or version == '*':
            version = next(iter(versions), '')
        if not version:
            raise ProjectError(f'no versions available for {id}')
        elif version not in versions:
            raise ProjectError(f'no such version: {version!r} ({id})')
        info = versions[version]
        if 'error' in info:
            raise ProjectError(info['error'])

        urls = info.get('resource_urls', [])

        return dict(
            id=id,
            version=version,
            type=project['type'],
            label=project['label'],
            language=project['language'],
            license=info.get('license', project.get('license')),
            resource_urls=urls,
            cache=_get_cache_path_for_urls(self, urls),
        )

    def get_cache_path(self, url: str) -> Path:
        """Return the path for caching *url*.

        Note that in general this is just a path operation and does
        not signify that the file exists in the file system.

        """
        filename = short_hash(url)
        return self.downloads_directory / filename

    def update(self, data: dict) -> None:
        """Update the configuration with items in *data*.

        Items are only inserted or replaced, not deleted. If a project
        index is provided in the ``"index"`` key, then either the
        project must not already be indexed or any project fields
        (label, language, or license) that are specified must be equal
        to the indexed project.

        """
        if 'data_directory' in data:
            self.data_directory = data['data_directory']
        for id, project in data.get('index', {}).items():
            if id in self._projects:
                # validate that they are the same
                _project = self._projects[id]
                for attr in ('label', 'language', 'license'):
                    if attr in project and project[attr] != _project[attr]:
                        raise ConfigurationError(f'{attr} mismatch for {id}')
            else:
                self.add_project(
                    id,
                    type=project.get('type', _WORDNET),
                    label=project.get('label'),
                    language=project.get('language'),
                    license=project.get('license'),
                    error=project.get('error'),
                )
            for version, info in project.get('versions', {}).items():
                if 'url' in info and 'error' in project:
                    raise ConfigurationError(
                        f'{id}:{version} url specified with default error'
                    )
                self.add_project_version(
                    id,
                    version,
                    url=info.get('url'),
                    license=info.get('license'),
                    error=info.get('error'),
                )

    def load_index(self, path: AnyPath) -> None:
        """Load and update with the project index at *path*.

        The project index is a TOML_ file containing project and
        version information. For example:

        .. code-block:: toml

           [ewn]
             label = "Open English WordNet"
             language = "en"
             license = "https://creativecommons.org/licenses/by/4.0/"
             [ewn.versions.2019]
               url = "https://en-word.net/static/english-wordnet-2019.xml.gz"
             [ewn.versions.2020]
               url = "https://en-word.net/static/english-wordnet-2020.xml.gz"

        .. _TOML: https://toml.io

        """
        path = Path(path).expanduser()
        with path.open('rb') as indexfile:
            try:
                index = tomli.load(indexfile)
            except tomli.TOMLDecodeError as exc:
                raise ConfigurationError('malformed index file') from exc
        self.update({'index': index})


def _get_cache_path_for_urls(
    config: WNConfig,
    urls: Sequence[str],
) -> Optional[Path]:
    for url in urls:
        path = config.get_cache_path(url)
        if path.is_file():
            return path
    return None


config = WNConfig()
with resources.path('wn', 'index.toml') as index_path:
    config.load_index(index_path)
