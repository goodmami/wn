"""Non-public Wn utilities."""

from typing import TypeVar, Iterable, List
import sys
from pathlib import Path
import hashlib
from unicodedata import normalize, combining
# version check is for mypy; see https://github.com/python/mypy/issues/1153
if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources  # noqa: F401


def is_url(string: str) -> bool:
    """Return True if *string* appears to be a URL."""
    # TODO: ETags?
    return any(string.startswith(scheme)
               for scheme in ('http://', 'https://'))


def is_gzip(path: Path) -> bool:
    """Return True if the file at *path* appears to be gzipped."""
    return _inspect_file_signature(path, b'\x1F\x8B')


def is_lzma(path: Path) -> bool:
    """Return True if the file at *path* appears to be lzma-compressed."""
    return _inspect_file_signature(path, b'\xFD7zXZ\x00')


def is_xml(path: Path) -> bool:
    """Return True if the file at *path* appears to be an XML file."""
    return _inspect_file_signature(path, b'<?xml ')


def _inspect_file_signature(path: Path, signature: bytes) -> bool:
    if path.is_file():
        with path.open('rb') as f:
            return f.read(len(signature)) == signature
    return False


def short_hash(string: str) -> str:
    """Return a short hash of *string*."""
    b2 = hashlib.blake2b(digest_size=20)
    b2.update(string.encode('utf-8'))
    return b2.hexdigest()


T = TypeVar('T')


def flatten(iterable: Iterable[Iterable[T]]) -> List[T]:
    return [x for xs in iterable for x in xs]


def normalize_form(s: str) -> str:
    return ''.join(c for c in normalize('NFKD', s.lower()) if not combining(c))
