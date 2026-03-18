"""
Local configuration settings.
"""

from collections.abc import Sequence
from enum import Enum
from fnmatch import fnmatch
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any, TypedDict

try:
    # python_version >= 3.11
    import tomllib  # type: ignore
except ImportError:
    import tomli as tomllib  # type: ignore

from wn._exceptions import ConfigurationError, ProjectError
from wn._types import AnyPath
from wn._util import (
    format_lexicon_specifier,
    is_str_key_dict,
    short_hash,
    split_lexicon_specifier,
)

# The index file is a project file of Wn
with as_file(files("wn") / "index.toml") as index_file:
    INDEX_FILE_PATH = index_file
# The directory where downloaded and added data will be stored.
DEFAULT_DATA_DIRECTORY = Path.home() / ".wn_data"
DATABASE_FILENAME = "wn.db"


class ResourceType(str, Enum):
    WORDNET = 'wordnet'
    ILI = 'ili'


class VersionInfo(TypedDict):
    resource_urls: list[str]
    license: str | None
    error: str | None


class ProjectInfo(TypedDict):
    type: ResourceType
    label: str | None
    language: str | None
    license: str | None
    error: str | None
    versions: dict[str, VersionInfo]


class ResolvedProjectInfo(TypedDict):
    id: str
    version: str
    type: ResourceType
    label: str | None
    language: str | None
    license: str | None
    resource_urls: list[str]
    cache: Path | None


class CacheEntry(TypedDict):
    path: Path
    id: str | None
    version: str | None
    url: str | None


class WNConfig:
    _projects: dict[str, ProjectInfo]

    def __init__(self):
        self._data_directory = DEFAULT_DATA_DIRECTORY
        self._projects = {}
        self._dbpath = self._data_directory / DATABASE_FILENAME
        self.allow_multithreading = False

    @property
    def data_directory(self) -> Path:
        """The file system directory where Wn's data is stored.

        Assign a new path to change where the database and downloads
        are stored.

        >>> wn.config.data_directory = "~/.cache/wn"
        >>> wn.config.database_path
        PosixPath('/home/username/.cache/wn/wn.db')
        >>> wn.config.downloads_directory
        PosixPath('/home/username/.cache/wn/downloads')

        """
        dir = self._data_directory
        dir.mkdir(exist_ok=True)
        return dir

    @data_directory.setter
    def data_directory(self, path: AnyPath) -> None:
        dir = Path(path).expanduser()
        if dir.exists() and not dir.is_dir():
            raise ConfigurationError(f"path exists and is not a directory: {dir}")
        self._data_directory = dir
        self._dbpath = dir / DATABASE_FILENAME

    @property
    def database_path(self) -> Path:
        """The path to the database file.

        The database path is derived from :attr:`data_directory` and
        cannot be changed directly.

        """
        return self._dbpath

    @property
    def downloads_directory(self) -> Path:
        """The file system directory where downloads are cached.

        The downloads directory is derived from :attr:`data_directory`
        and cannot be changed directly.

        """
        dir = self.data_directory / "downloads"
        dir.mkdir(exist_ok=True)
        return dir

    @property
    def index(self) -> dict[str, ProjectInfo]:
        """The project index."""
        return self._projects

    def add_project(
        self,
        id: str,
        type: ResourceType = ResourceType.WORDNET,
        label: str | None = None,
        language: str | None = None,
        license: str | None = None,
        error: str | None = None,
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
            raise ValueError(f"project already added: {id}")
        self._projects[id] = ProjectInfo(
            type=ResourceType(type),
            label=label,
            language=language,
            license=license,
            error=error,
            versions={},
        )

    def add_project_version(
        self,
        id: str,
        version: str,
        url: str | None = None,
        error: str | None = None,
        license: str | None = None,
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
        if url and error:
            spec = format_lexicon_specifier(id, version)
            raise ConfigurationError(f"{spec} specifies both url and redirect")

        version_data = VersionInfo(
            resource_urls=url.split() if (url and not error) else [],
            license=license,
            error=error,
        )
        project = self._projects[id]
        project["versions"][version] = version_data

    def get_project_info(self, arg: str) -> ResolvedProjectInfo:
        """Return information about an indexed project version.

        If the project has been downloaded and cached, the ``"cache"``
        key will point to the path of the cached file, otherwise its
        value is ``None``.

        Arguments:
            arg: a project specifier

        Example:

            >>> info = wn.config.get_project_info("oewn:2021")
            >>> info["label"]
            'Open English WordNet'

        """
        id, version = split_lexicon_specifier(arg)
        if id not in self._projects:
            raise ProjectError(f"no such project id: {id}")
        project: ProjectInfo = self._projects[id]
        if project["error"]:
            raise ProjectError(project["error"])

        versions: dict = project["versions"]
        if not version or version == "*":
            version = next(iter(versions), "")
        if not version:
            raise ProjectError(f"no versions available for {id}")
        elif version not in versions:
            raise ProjectError(f"no such version: {version!r} ({id})")
        info = versions[version]
        if info["error"]:
            raise ProjectError(info["error"])

        urls = info.get("resource_urls", [])

        return ResolvedProjectInfo(
            id=id,
            version=version,
            type=project["type"],
            label=project["label"],
            language=project["language"],
            license=info.get("license", project.get("license")),
            resource_urls=urls,
            cache=_get_cache_path_for_urls(self, urls),
        )

    def get_cache_path(self, url: str) -> Path:
        """Return the path for caching *url*.

        Note that this is just a path operation and does
        not signify that the file exists in the file system.

        """
        filename = short_hash(url)
        return self.downloads_directory / filename

    def list_cache_entries(self, arg: str = "*") -> list[CacheEntry]:
        """Return a list of cached resources.

        Use *arg* as a pattern to match project specifiers. It
        defaults to `"*"` to select all cached entries.

        Each entry on the list is a dictionary with the keys:
        * `"path"` -- the path of the cached file
        * `"id"`  -- the ID of the cached resource
        * `"version"` -- the version of the cached resource
        * `"url"` -- the URL of the cached resource

        Note that cached files are stored with a hash of their URL as
        the filename and that it is not feasible to recover the URL
        from the hash alone. Therefore, for lexicons downloaded with a
        URL that does not appear in the index, the ID, version, and URL
        and will be :python:`None` instead.
        """
        arg = arg.strip()
        cache_map = _cache_map(self)
        entries: list[CacheEntry] = []
        for cache_path in self.downloads_directory.iterdir():
            if cache_path in cache_map:
                id, version, url = cache_map[cache_path]
                specifier = format_lexicon_specifier(id, version)
                if not (fnmatch(specifier, arg) or url == arg):
                    continue
                entries.append(
                    CacheEntry(path=cache_path, id=id, version=version, url=url)
                )
            elif arg in ("*", "*:*"):
                entries.append(
                    CacheEntry(path=cache_path, id=None, version=None, url=None)
                )
        return entries

    def update(self, data: dict[str, Any]) -> None:
        """Update the configuration with items in *data*.

        Items are only inserted or replaced, not deleted. If a project
        index is provided in the ``"index"`` key, then either the
        project must not already be indexed or any project fields
        (label, language, or license) that are specified must be equal
        to the indexed project.

        """
        if datadir := data.get("data_directory"):
            if not isinstance(datadir, (str, Path)):
                raise ConfigurationError(
                    "data_directory must be a str or Path, "
                    f"not {type(datadir).__name__}"
                )
            self.data_directory = datadir
        if index := data.get("index", {}):
            if not is_str_key_dict(index):
                raise ConfigurationError("index must be a dict with str keys")
            self._update_index(index)

    def _update_index(self, index: dict[str, Any]) -> None:
        for id, project in index.items():
            if not is_str_key_dict(project):
                raise ConfigurationError(f"invalid project: {project}")
            if id in self._projects:
                # validate that they are the same
                _project = self._projects[id]
                for attr in ("label", "language", "license"):
                    if attr in project and project[attr] != _project[attr]:
                        raise ConfigurationError(f"{attr} mismatch for {id}")
            else:
                self.add_project(
                    id,
                    type=project.get("type", ResourceType.WORDNET),
                    label=project.get("label"),
                    language=project.get("language"),
                    license=project.get("license"),
                    error=project.get("error"),
                )
            for version, info in project.get("versions", {}).items():
                if info.get("url") and project.get("error"):
                    spec = format_lexicon_specifier(id, version)
                    raise ConfigurationError(f"{spec} url specified with default error")
                self.add_project_version(
                    id,
                    version,
                    url=info.get("url"),
                    license=info.get("license"),
                    error=info.get("error"),
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
        with path.open("rb") as indexfile:
            try:
                index = tomllib.load(indexfile)
            except tomllib.TOMLDecodeError as exc:
                raise ConfigurationError("malformed index file") from exc
            if not is_str_key_dict(index):
                raise ConfigurationError("invalid index file")
        self.update({"index": index})


def _get_cache_path_for_urls(
    config: WNConfig,
    urls: Sequence[str],
) -> Path | None:
    for url in urls:
        path = config.get_cache_path(url)
        if path.is_file():
            return path
    return None


def _cache_map(config: WNConfig) -> dict[str, tuple[str, str, str]]:
    """Return a dict of cache hashes to resource info tuples.

    Each tuple contains the id, version, and URL of the indexed
    resource. The hash is based on the URL and the tuple only contains
    information from the index. They do not indicate whether the
    resource has been cached.
    """
    return {
        config.get_cache_path(url): (id, version, url)
        for id, p_info in config.index.items()
        for version, v_info in p_info["versions"].items()
        for url in v_info["resource_urls"]
    }


config = WNConfig()
config.load_index(INDEX_FILE_PATH)
