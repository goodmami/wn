
"""
Local configuration settings.
"""

from typing import Dict
from pathlib import Path

import toml

from wn import Error
from wn._types import AnyPath
from wn.constants import _WORDNET
from wn._util import is_url, resources, short_hash

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
            raise Error(f'path exists and is not a directory: {dir}')
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
    ) -> None:
        """Add a new wordnet project to the index.

        Arguments:
            id: short identifier of the project
            label: full name of the project
            language: `BCP 47`_ language code of the resource
            license: link or name of the project's default license

        .. _BCP 47: https://en.wikipedia.org/wiki/IETF_language_tag
        """
        if id in self._projects:
            raise ValueError(f'project already added: {id}')
        self._projects[id] = {
            'type': type,
            'label': label,
            'language': language,
            'versions': {},
            'license': license
        }

    def add_project_version(
            self,
            id: str,
            version: str,
            url: str,
            license: str = None,
    ) -> None:
        """Add a new resource version for a project.

        Arguments:
            id: short identifier of the project
            version: version string of the resource
            url: web address of the resource
            license: link or name of the resource's license; if not
              given, the project's default license will be used.

        """
        version_data = {'resource_url': url}
        if license:
            version_data['license'] = license
        project = self._projects[id]
        project['versions'][version] = version_data

    def get_project_info(self, arg: str) -> Dict:
        """Return a dictionary of information about an indexed project.

        If the project has been downloaded and cached, the ``"cache"``
        key will point to the path of the cached file, otherwise its
        value is ``None``.

        Arguments:
            arg: a project specifier

        Example:

            >>> info = wn.config.get_project_info('pwn:3.0')
            >>> info['label']
            'Princeton WordNet'

        """
        id, _, version = arg.partition(':')
        project: Dict = self._projects[id]
        versions: Dict = project['versions']
        if not version or version == '*':
            version = next(iter(versions))
        if version not in versions:
            raise Error(f'no such version: {version!r} ({project})')

        url = versions[version]['resource_url']
        cache_path = self.get_cache_path(url)

        return dict(
            id=id,
            version=version,
            type=project['type'],
            label=project['label'],
            language=project['language'],
            license=versions[version].get('license', project.get('license')),
            resource_url=url,
            cache=cache_path if cache_path.exists() else None
        )

    def get_cache_path(self, arg: str) -> Path:
        """Return the path for caching *arg*.

        The *arg* argument may be either a URL or a project specifier
        that gets passed to :meth:`get_project_info`. Note that this
        is just a path operation and does not signify that the file
        exists in the file system.

        """
        if not is_url(arg):
            arg = self.get_project_info(arg)['resource_url']
        filename = short_hash(arg)
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
                        raise Error(f'{attr} mismatch for {id}')
            else:
                self.add_project(
                    id,
                    type=project.get('type', _WORDNET),
                    label=project.get('label'),
                    language=project.get('language'),
                    license=project.get('license'),
                )
            for version, info in project.get('versions', {}).items():
                self.add_project_version(
                    id,
                    version,
                    info['url'],
                    license=info.get('license'),
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
        index = toml.load(path)
        self.update({'index': index})


config = WNConfig()
with resources.path('wn', 'index.toml') as index_path:
    config.load_index(index_path)
