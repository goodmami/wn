
from typing import Sequence, TextIO
import sys
from pathlib import Path


def is_gzip(path: Path) -> bool:
    """Return True if the file at *path* appears to be gzipped."""
    with path.open('rb') as f:
        return f.read(2) == b'\x1F\x8B'


def progress_bar(
        message: str = '',
        max: int = 0,
        width: int = 30,
        fmt: str = '\r{message}[{fill:<{width}}] ({current}/{max})',
        fillchars: Sequence[str] = '#',
        file: TextIO = sys.stderr):
    """
    Return a generator which yields a progres bar string.

    Update the counter with the generator's send() method giving an
    incremement value. Normally you'd want to print with end='' to
    keep the progress bar on the same line.

    Example:
        >>> p = progress_bar('Progress: ', max=10, width=10)
        >>> print(p.send(3))
        Progress: [###       ] (3/10)
    """

    assert width >= 1, 'width must be 1 or greater'
    fillnum = len(fillchars)
    assert fillnum > 0, 'fillchars must be 1 or more characters'
    step = max / width
    fillchars = [''] + list(fillchars)

    def fill(current: int) -> str:
        if max > 0:
            done = int((current / max) * width) * fillchars[-1]
            part = fillchars[int(((current % step) / step) * len(fillchars))]
            return done + part
        else:
            return '-' * width

    def update():
        data = {'message': message, 'fill': '', 'width': width,
                'current': 0, 'max': max or '?'}
        while True:
            data['fill'] = fill(data['current'])
            s = fmt.format(**data)
            if file:
                print('\r\033[K', end='', file=file)
                print(s, end='', file=file)
            increment = yield s
            data['current'] = min(data['current'] + increment, max)

    generator = update()
    next(generator)
    return generator
