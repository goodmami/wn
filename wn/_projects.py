from typing import Dict

from wn import Error


PROJECTS = {
    'ewn': {
        'label': 'English WordNet',
        'language': 'en',
        'versions': {
            '2020': {
                'resource_url': 'https://en-word.net/static/english-wordnet-2020.xml.gz',
                'license': 'https://creativecommons.org/licenses/by/4.0/',
            },
        }
    },
}


def get_project_info(project: str, version: str = None) -> Dict:
    if project not in PROJECTS:
        raise Error(f'no such project: {project}')
    project_info = PROJECTS[project]
    versions = project_info['versions']
    if version is None:
        version = next(iter(versions))
    if not isinstance(version, str):
        raise Error(f'version must be type {str!r}, not {type(version)!r}')
    if version not in versions:
        raise Error(f'no such version: {version!r} ({project})')
    return dict(
        project=project,
        version=version,
        label=project_info['label'],
        language=project_info['language'],
        resource_url=versions[version]['resource_url'],
    )
