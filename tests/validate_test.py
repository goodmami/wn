from collections.abc import Sequence
from pathlib import Path

from wn import lmf
from wn.validate import validate


def _assert_invalid(select: str, path: Path) -> None:
    lex = lmf.load(path, progress_handler=None)["lexicons"][0]
    report = validate(lex, select=[select], progress_handler=None)
    print(report)
    assert len(report[select]["items"]) > 0


def test_E101(datadir):
    _assert_invalid("E101", datadir / "E101-0.xml")
    _assert_invalid("E101", datadir / "E101-1.xml")
    _assert_invalid("E101", datadir / "E101-2.xml")
    _assert_invalid("E101", datadir / "E101-3.xml")
