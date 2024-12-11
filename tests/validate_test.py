import pytest

from wn import lmf
from wn.validate import validate

tests = [
    ("E101", 0),
    ("E101", 1),
    ("E101", 2),
    ("E101", 3),
    ("W305", 0),
    ("W306", 0),
    ("W307", 0),
]
test_ids = [f"{code}-{i}" for code, i in tests]


@pytest.mark.parametrize("code,i", tests, ids=test_ids)
def test_validate(datadir, code: str, i: int) -> None:
    path = datadir / f"{code}-{i}.xml"
    lex = lmf.load(path, progress_handler=None)["lexicons"][0]
    report = validate(lex, select=[code], progress_handler=None)
    print(report)
    assert len(report[code]["items"]) > 0
