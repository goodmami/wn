
"""
Wordnet and ILI Packages and Collections
"""

from collections.abc import Iterator
from typing import Optional
from pathlib import Path
import tarfile
import tempfile
from contextlib import contextmanager
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


def iterpackages(path: AnyPath) -> Iterator[Package]:
    """Yield any wordnet or ILI packages found at *path*.

    The *path* argument can point to one of the following:
      - a lexical resource file or ILI file
      - a wordnet package directory
      - a wordnet collection directory
      - a tar archive containing one of the above
      - a compressed (gzip or lzma) resource file or tar archive
    """
    path = Path(path).expanduser()

    if path.is_dir():
        if is_package_directory(path):
            yield Package(path)

        elif is_collection_directory(path):
            yield from Collection(path).packages()

        else:
            raise wn.Error(
                f'does not appear to be a valid package or collection: {path!s}'
            )

    elif tarfile.is_tarfile(path):
        with tarfile.open(path) as tar:
            _check_tar(tar)
            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extractall(path=tmpdir)
                contents = list(Path(tmpdir).iterdir())
                if len(contents) != 1:
                    raise wn.Error(
                        'archive may only have one resource, package, or collection'
                    )
                yield from iterpackages(contents[0])

    else:
        decompressed: Path
        with _get_decompressed(path) as decompressed:
            if lmf.is_lmf(decompressed) or _ili.is_ili(decompressed):
                yield ResourceOnlyPackage(decompressed)
            else:
                raise wn.Error(
                    f'not a valid lexical resource: {path!s}'
                )


@contextmanager
def _get_decompressed(source: Path) -> Iterator[Path]:
    gzipped = is_gzip(source)
    xzipped = is_lzma(source)
    if not (gzipped or xzipped):
        yield source
    else:
        tmp = tempfile.NamedTemporaryFile(suffix='.xml', delete=False)
        path = Path(tmp.name)
        try:
            # for typing issues, see https://github.com/python/mypy/issues/15031
            if gzipped:
                with gzip.open(source, 'rb') as gzip_src:
                    shutil.copyfileobj(gzip_src, tmp)  # type: ignore
            else:  # xzipped
                with lzma.open(source, 'rb') as lzma_src:
                    shutil.copyfileobj(lzma_src, tmp)  # type: ignore

            tmp.close()  # Windows cannot reliably reopen until it's closed

            yield path

        except (OSError, EOFError, lzma.LZMAError) as exc:
            raise wn.Error(f'could not decompress file: {source}') from exc

        finally:
            path.unlink()


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
