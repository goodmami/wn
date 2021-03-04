
from typing import Iterator, Dict
from pathlib import Path

from wn._types import AnyPath


def is_ili(source: AnyPath) -> bool:
    """Return True if *source* is an ILI tab-separated-value file.

    This only checks that the first column, split by tabs, of the
    first line is 'ili' or 'ILI'. It does not check if each line has
    the correct number of columns.

    """
    source = Path(source).expanduser()
    if source.is_file():
        try:
            with source.open('rb') as fh:
                return next(fh).split(b'\t')[0] in (b'ili', b'ILI')
        except (StopIteration, IndexError):
            pass
    return False


def load(source: AnyPath) -> Iterator[Dict[str, str]]:
    """Load an interlingual index file.

    Args:
        source: path to an ILI file
    """
    source = Path(source).expanduser()
    with source.open(encoding='utf-8') as fh:
        header = next(fh).rstrip('\r\n')
        fields = tuple(map(str.lower, header.split('\t')))
        for line in fh:
            yield dict(zip(fields, line.rstrip('\r\n').split('\t')))
