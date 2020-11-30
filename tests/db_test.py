
from wn import _db


def test_schema_compatibility():
    assert _db.is_schema_compatible(create=True)
