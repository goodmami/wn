
from typing import (
    TypeVar, Iterable, Sequence, List, TextIO, Callable, Any
)
import sys
from pathlib import Path
import hashlib
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


class ProgressBar:
    """A class for formatting progress as a bar.

    Update the counter with the update() method giving an incremement
    value.

    Example:
        >>> p = ProgressBar('Progress: ', max=10, width=10)
        >>> p.update(3)
        Progress: [###       ] (3/10)

    """

    def __init__(
            self,
            message: str = '',
            end: str = '',
            max: int = 0,
            width: int = 30,
            unit: str = '\b',
            status: str = '\b',
            fmt: str = '\r{message} [{fill:<{width}}] ({count}/{max} {unit}) {status}',
            fillchars: Sequence[str] = '#',
            file: TextIO = sys.stderr,
            **kwargs,
    ):
        assert width >= 1, 'width must be 1 or greater'
        assert len(fillchars) > 0, 'fillchars must be 1 or more characters'
        self.width = width
        self.fmt = fmt
        self.fillchars = [''] + list(fillchars)
        self.file = file
        kwargs['count'] = 0
        kwargs['max'] = max
        kwargs['message'] = message
        kwargs['unit'] = unit
        kwargs['status'] = status
        self.kwargs = kwargs

    def update(self, n: int = 1, **kwargs) -> str:
        width = self.width
        _kw = self.kwargs
        if kwargs:
            _kw.update(kwargs)

        _kw['count'] += n
        count = _kw['count']
        max = _kw['max']

        if max > 0:
            _chars = self.fillchars
            _count = min(count, max)
            _step = (max / width)
            _done = int((_count / max) * width) * _chars[-1]
            _part = _chars[int(((_count % _step) / _step) * len(_chars))]
            fill = _done + _part
        else:
            fill = '-' * width

        s = self.fmt.format(fill=fill, width=width, **_kw)
        if self.file:
            print('\r\033[K', end='', file=self.file)
            print(s, end='', file=self.file)
        return s

    @staticmethod
    def noop_update(n: int = 1, **kwargs) -> str:
        return ''


def get_progress_handler(
        arg: Any, message: str, unit: str, status: str,
) -> Callable[..., str]:
    # this function serves as a sentinel for the default behavior
    if arg is get_progress_handler:
        if sys.stderr.isatty():
            return ProgressBar(
                message, unit=unit, status=status, file=sys.stderr
            ).update
        else:
            return ProgressBar.noop_update
    elif arg is None:
        return ProgressBar.noop_update
    elif callable(arg):
        return arg
    else:
        raise TypeError(f'not None or callable: {arg}')
