
"""
Local configuration settings.
"""

from typing import Dict
from pathlib import Path

from wn import Error

# The directory where downloaded and added data will be stored.
DEFAULT_DATA_DIRECTORY = Path.home() / '.wn_data'
DEFAULT_DATABASE_FILENAME = 'wn.db'


class WNConfig:

    def __init__(self):
        self._data_directory = DEFAULT_DATA_DIRECTORY
        self._projects = {}
        self.database_filename = DEFAULT_DATABASE_FILENAME

    @property
    def data_directory(self) -> Path:
        dir = self._data_directory
        dir.mkdir(exist_ok=True)
        return dir

    @data_directory.setter
    def data_directory(self, path):
        dir = Path(path).expanduser()
        if dir.exists() and not dir.is_dir():
            raise Error(f'path exists and is not a directory: {dir}')
        self._data_directory = dir

    @property
    def database_path(self):
        return self.data_directory / self.database_filename

    @property
    def downloads_directory(self):
        dir = self.data_directory / 'downloads'
        dir.mkdir(exist_ok=True)
        return dir

    def add_project(
            self,
            name: str,
            label: str,
            language: str,
            license: str = None,
    ) -> None:
        """Add a new wordnet project to the index."""
        if name in self._projects:
            raise ValueError(f'project already added: {name}')
        self._projects[name] = {
            'label': label,
            'language': language,
            'versions': {},
            'license': license
        }

    def add_project_version(
            self,
            name: str,
            version: str,
            url: str,
            license: str = None,
    ) -> None:
        """Add a new resource version for a project."""
        version_data = {'resource_url': url}
        if license:
            version_data['license'] = license
        project = self._projects[name]
        project['versions'][version] = version_data

    def get_project_info(self, arg: str) -> Dict:
        name, _, version = arg.partition(':')
        project: Dict = self._projects[name]
        versions: Dict = project['versions']
        if not version or version == '*':
            version = next(iter(versions))
        if version not in versions:
            raise Error(f'no such version: {version!r} ({project})')
        return dict(
            project=name,
            version=version,
            label=project['label'],
            language=project['language'],
            license=versions[version].get('license', project.get('license')),
            resource_url=versions[version]['resource_url'],
        )


config = WNConfig()

config.add_project('ewn', 'English WordNet', 'en')
config.add_project_version(
    'ewn', '2020',
    'https://en-word.net/static/english-wordnet-2020.xml.gz',
    'https://creativecommons.org/licenses/by/4.0/',
)
config.add_project_version(
    'ewn', '2019',
    'https://en-word.net/static/english-wordnet-2019.xml.gz',
    'https://creativecommons.org/licenses/by/4.0/',
)
