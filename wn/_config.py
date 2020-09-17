
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
        dir = Path(path)
        if dir.exists() and not dir.is_dir():
            raise Error(f'path exists and is not a directory: {dir}')
        self._data_directory = dir

    @property
    def database_path(self):
        return self._data_directory / self.database_filename

    @property
    def downloads_directory(self):
        dir = self.data_directory / 'downloads'
        dir.mkdir(exist_ok=True)
        return dir

    def add_project(self, name: str, label: str, language: str) -> None:
        if name in self._projects:
            raise ValueError(f'project already added: {name}')
        self._projects[name] = {
            'label': label,
            'language': language,
            'versions': {},
        }

    def add_project_version(
            self,
            name: str,
            version: str,
            url: str,
            license: str
    ) -> None:
        project = self._projects[name]
        project['versions'][version] = {
            'resource_url': url,
            'license': license,
        }

    def get_project_info(self, name: str, version: str = None) -> Dict:
        project: Dict = self._projects[name]
        versions: Dict = project['versions']
        if version is None:
            version = next(iter(versions))
        if not isinstance(version, str):
            raise Error(f'version must be type {str!r}, not {type(version)!r}')
        if version not in versions:
            raise Error(f'no such version: {version!r} ({project})')
        return dict(
            project=name,
            version=version,
            label=project['label'],
            language=project['language'],
            resource_url=versions[version]['resource_url'],
        )


config = WNConfig()

config.add_project('ewn', 'English WordNet', 'en')
config.add_project_version(
    'ewn', '2020',
    'https://en-word.net/static/english-wordnet-2020.xml.gz',
    'https://creativecommons.org/licenses/by/4.0/',
)
