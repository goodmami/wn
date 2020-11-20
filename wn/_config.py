
"""
Local configuration settings.
"""

from typing import Dict
from pathlib import Path

import toml

from wn import Error
from wn._types import AnyPath
from wn._util import resources

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

    def update(self, data: dict) -> None:
        if 'data_directory' in data:
            self.data_directory = data['data_directory']
        for name, project in data.get('index', {}).items():
            if name in self._projects:
                # validate that they are the same
                _project = self._projects[name]
                for attr in ('label', 'language', 'license'):
                    if attr in project and project[attr] != _project[attr]:
                        raise Error(f'{attr} mismatch for {name}')
            else:
                self.add_project(
                    name,
                    project['label'],
                    project['language'],
                    license=project.get('license'),
                )
            for version, info in project.get('versions', {}).items():
                self.add_project_version(
                    name,
                    version,
                    info['url'],
                    license=project.get('license'),
                )

    def load_index(self, path: AnyPath) -> None:
        path = Path(path).expanduser()
        index = toml.load(path)
        self.update({'index': index})


config = WNConfig()
with resources.path('wn', 'index.toml') as index_path:
    config.load_index(index_path)
