
"""
Wordnet and ILI Packages and Collections
"""

from collections.abc import Iterator
from typing import Optional
from pathlib import Path
import tarfile
import tempfile
import gzip
import lzma
import shutil


import wn
from wn._types import AnyPath
from wn.constants import _WORDNET, _ILI
from wn._util import is_gzip, is_lzma
from wn import lmf
from wn import _ili


_ADDITIONAL_FILE_SUFFIXES = ('', '.txt', '.md', '.rst')


def is_package_directory(path: AnyPath) -> bool:
    """Return ``True`` if *path* appears to be a wordnet or ILI package."""
    path = Path(path).expanduser()
    return len(_package_directory_types(path)) == 1


def _package_directory_types(path: Path) -> list[tuple[Path, str]]:
    types: list[tuple[Path, str]] = []
    if path.is_dir():
        for p in path.iterdir():
            typ = _resource_file_type(p)
            if typ is not None:
                types.append((p, typ))
    return types


def _resource_file_type(path: Path) -> Optional[str]:
    if lmf.is_lmf(path):
        return _WORDNET
    elif _ili.is_ili(path):
        return _ILI
    return None


def is_collection_directory(path: AnyPath) -> bool:
    """Return ``True`` if *path* appears to be a wordnet collection."""
    path = Path(path).expanduser()
    return (path.is_dir()
            and len(list(filter(is_package_directory, path.iterdir()))) >= 1)


class Project:
    """The base class for packages and collections."""

    __slots__ = '_path',

    def __init__(self, path: AnyPath):
        self._path: Path = Path(path).expanduser()

    @property
    def path(self) -> Path:
        """The path of the project directory or resource file.

        For :class:`Package` and :class:`Collection` objects, the path
        is its directory. For :class:`ResourceOnlyPackage` objects,
        the path is the same as from
        :meth:`resource_file() <Package.resource_file>`
        """
        return self._path

    def readme(self) -> Optional[Path]:
        """Return the path of the README file, or :data:`None` if none exists."""
        return self._find_file(self._path / 'README', _ADDITIONAL_FILE_SUFFIXES)

    def license(self) -> Optional[Path]:
        """Return the path of the license, or :data:`None` if none exists."""
        return self._find_file(self._path / 'LICENSE', _ADDITIONAL_FILE_SUFFIXES)

    def citation(self) -> Optional[Path]:
        """Return the path of the citation, or :data:`None` if none exists."""
        return self._find_file(self._path / 'citation', ('.bib',))

    def _find_file(self, base: Path, suffixes: tuple[str, ...]) -> Optional[Path]:
        for suffix in suffixes:
            base = base.with_suffix(suffix)
            if base.is_file():
                return base
        return None


class Package(Project):
    """A wordnet or ILI package.

    A package is a directory with a resource file and optional
    metadata files.

    """

    @property
    def type(self) -> Optional[str]:
        """Return the name of the type of resource contained by the package.

        Valid return values are:
        - :python:`"wordnet"` -- the resource is a WN-LMF lexicon file
        - :python:`"ili"` -- the resource is an interlingual index file
        - :data:`None` -- the resource type is undetermined
        """
        return _resource_file_type(self.resource_file())

    def resource_file(self) -> Path:
        """Return the path of the package's resource file."""
        files = _package_directory_types(self._path)
        if not files:
            raise wn.Error(f'no resource found in package: {self._path!s}')
        elif len(files) > 1:
            raise wn.Error(f'multiple resource found in package: {self._path!s}')
        return files[0][0]


class ResourceOnlyPackage(Package):
    """A virtual package for a single-file resource.

    This class is for resource files that are not distributed in a
    package directory. The :meth:`readme() <Project.readme>`,
    :meth:`license() <Project.license>`, and
    :meth:`citation() <Project.citation>` methods all return
    :data:`None`.
    """

    def resource_file(self) -> Path:
        return self._path

    def readme(self): return None
    def license(self): return None
    def citation(self): return None


class Collection(Project):
    """A wordnet or ILI collection

    Collections are directories that contain package directories and
    optional metadata files.
    """

    def packages(self) -> list[Package]:
        """Return the list of packages in the collection."""
        return [Package(path)
                for path in self._path.iterdir()
                if is_package_directory(path)]


def get_project(
    *,
    project: Optional[str] = None,
    path: Optional[AnyPath] = None,
) -> Project:
    """Return the :class:`Project` object for *project* or *path*.

    The *project* argument is a project specifier and will look in the
    download cache for the project data. If the project has not been
    downloaded and cached, an error will be raised.

    The *path* argument looks for project data at the given path. It
    can point to a resource file, a package directory, or a collection
    directory. Unlike :func:`iterpackages`, this function does not
    iterate over packages within a collection, and instead the
    :class:`Collection` object is returned.

    .. note::

       If the target is compressed or archived, the data will be
       extracted to a temporary directory. It is the user's
       responsibility to delete this temporary directory, which is
       indicated by :data:`Project.path`.
    """
    if project and path:
        raise TypeError('expected a project specifier or a path, not both')
    if not project and not path:
        raise TypeError('expected a project specifier or a path')

    if project:
        info = wn.config.get_project_info(project)
        if not info['cache']:
            raise wn.Error(
                f'{project} is not cached; try `wn.download({project!r}` first'
            )
        path = info['cache']
    assert path

    proj, _ = _get_project_from_path(path)
    return proj


def _get_project_from_path(
    path: AnyPath, tmp_path: Optional[Path] = None,
) -> tuple[Project, Optional[Path]]:
    path = Path(path).expanduser()

    if path.is_dir():
        if is_package_directory(path):
            return Package(path), tmp_path

        elif is_collection_directory(path):
            return Collection(path), tmp_path

        else:
            raise wn.Error(
                f'does not appear to be a valid package or collection: {path!s}'
            )

    elif tarfile.is_tarfile(path):
        tmpdir_ = Path(tempfile.mkdtemp())
        with tarfile.open(path) as tar:
            _check_tar(tar)
            tar.extractall(path=tmpdir_)
            contents = list(tmpdir_.iterdir())
            if len(contents) != 1:
                raise wn.Error(
                    'archive may only have one resource, package, or collection'
                )
            return _get_project_from_path(contents[0], tmp_path=tmpdir_)

    else:
        decompressed, tmp_path = _get_decompressed(path, tmp_path)
        if lmf.is_lmf(decompressed) or _ili.is_ili(decompressed):
            return ResourceOnlyPackage(decompressed), tmp_path
        else:
            raise wn.Error(
                f'not a valid lexical resource: {path!s}'
            )


def iterpackages(path: AnyPath, delete: bool = True) -> Iterator[Package]:
    """Yield any wordnet or ILI packages found at *path*.

    The *path* argument can point to one of the following:
      - a lexical resource file or ILI file
      - a wordnet package directory
      - a wordnet collection directory
      - a tar archive containing one of the above
      - a compressed (gzip or lzma) resource file or tar archive

    The *delete* argument determines whether any created temporary
    directories will be deleted after iteration is complete. When it
    is :data:`True`, the package objects can only be inspected during
    iteration. If one needs persistent objects (e.g.,
    :python:`pkgs = list(iterpackages(...))`), then set *delete* to
    :data:`False`.

    .. warning::

       When *delete* is set to :data:`False`, the user is responsible
       for cleaning up any temporary directories. The
       :data:`Project.path` attribute indicates the path of the
       temporary directory.

    """
    project, tmp_path = _get_project_from_path(path)

    try:
        if isinstance(project, Package):
            yield project
        elif isinstance(project, Collection):
            yield from project.packages()
        else:
            raise wn.Error(f'unexpected project type: {project.__class__.__name__}')
    finally:
        if tmp_path and delete:
            if tmp_path.is_dir():
                shutil.rmtree(tmp_path)
            elif tmp_path.is_file():
                tmp_path.unlink()
            else:
                raise wn.Error(f'could not remove temporary path: {tmp_path}')


def _get_decompressed(
    source: Path,
    tmp_path: Optional[Path],
) -> tuple[Path, Optional[Path]]:
    gzipped = is_gzip(source)
    xzipped = is_lzma(source)
    if not (gzipped or xzipped):
        return source, tmp_path
    else:
        tmp = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
        path = Path(tmp.name)
        try:
            if gzipped:
                with gzip.open(source, 'rb') as gzip_src:
                    shutil.copyfileobj(gzip_src, tmp)
            else:  # xzipped
                with lzma.open(source, 'rb') as lzma_src:
                    shutil.copyfileobj(lzma_src, tmp)

            tmp.close()  # Windows cannot reliably reopen until it's closed

        except (OSError, EOFError, lzma.LZMAError) as exc:
            raise wn.Error(f'could not decompress file: {source}') from exc

        # if tmp_path is not None, the compressed file was in a
        # temporary directory, so return that. Otherwise the new path
        # becomes the tmp_path
        return path, tmp_path or path


def _check_tar(tar: tarfile.TarFile) -> None:
    """Check the tarfile to avoid potential security issues.

    Currently collections and packages have the following constraints:
    - Only regular files or directories
    - No paths starting with '/' or containing '..'
    """
    for info in tar.getmembers():
        if not (info.isfile() or info.isdir()):
            raise wn.Error(
                f'tarfile member is not a regular file or directory: {info.name}'
            )
        if info.name.startswith('/') or '..' in info.name:
            raise wn.Error(
                f'tarfile member paths may not be absolute or contain ..: {info.name}'
            )
