
from pathlib import Path


def is_gzip(path: Path) -> bool:
    """Return True if the file at *path* appears to be gzipped."""
    with path.open('rb') as f:
        return f.read(2) == b'\x1F\x8B'
