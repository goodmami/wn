import re
import urllib.request

from wn.lmf import SUPPORTED_VERSIONS, _SCHEMAS
from wn.constants import (
    SENSE_RELATIONS,
    SENSE_SYNSET_RELATIONS,
    SYNSET_RELATIONS,
)

# Simple cache so we don't re-download the same DTD multiple times
_DTD_CACHE: dict[str, str] = {}


def load_dtd(url: str) -> str:
    """Fetch and cache the DTD text for a given URL."""
    if url not in _DTD_CACHE:
        with urllib.request.urlopen(url) as f:
            _DTD_CACHE[url] = f.read().decode("utf-8")
    return _DTD_CACHE[url]


def extract_reltypes(dtd_text: str, element: str) -> set[str]:
    """
    Extract relType enumerations from:

        <!ATTLIST {element} ... relType (a|b|c|...) ...>

    `element` is typically "SynsetRelation" or "SenseRelation".
    """
    pattern = r"<!ATTLIST {elem}\s+[^>]*relType\s*\(([^)]*)\)".format(
        elem=re.escape(element)
    )
    m = re.search(pattern, dtd_text, flags=re.MULTILINE | re.DOTALL)
    if not m:
        return set()

    raw = m.group(1)
    parts = [p.strip() for p in raw.split("|")]
    return {p for p in parts if p}


def test_relation_types_in_constants() -> None:
    """
    For each supported LMF version, confirm that all relation types
    declared in the DTD appear in the internal constants.

    - SynsetRelation.relType ⊆ SYNSET_RELATIONS
    - SenseRelation.relType ⊆ SENSE_RELATIONS ∪ SENSE_SYNSET_RELATIONS
    """

    failures: list[str] = []

    allowed_sense_reltypes = SENSE_RELATIONS | SENSE_SYNSET_RELATIONS

    for version in sorted(SUPPORTED_VERSIONS):
        dtd_url = _SCHEMAS[version]
        dtd = load_dtd(dtd_url)

        synset_reltypes = extract_reltypes(dtd, "SynsetRelation")
        sense_reltypes = extract_reltypes(dtd, "SenseRelation")

        # Sanity checks: make sure we actually found the enumerations
        if not synset_reltypes:
            failures.append(
                f"LMF {version}: no SynsetRelation relType enumeration "
                f"found in DTD {dtd_url}"
            )
        if not sense_reltypes:
            failures.append(
                f"LMF {version}: no SenseRelation relType enumeration "
                f"found in DTD {dtd_url}"
            )

        missing_synset = synset_reltypes - SYNSET_RELATIONS
        missing_sense = sense_reltypes - allowed_sense_reltypes

        if missing_synset or missing_sense:
            lines: list[str] = [f"LMF {version}:"]
            if missing_synset:
                lines.append(
                    "  SynsetRelation relTypes missing in SYNSET_RELATIONS: "
                    + ", ".join(sorted(missing_synset))
                )
            if missing_sense:
                lines.append(
                    "  SenseRelation relTypes missing in "
                    "SENSE_RELATIONS ∪ SENSE_SYNSET_RELATIONS: "
                    + ", ".join(sorted(missing_sense))
                )
            failures.append("\n".join(lines))

    if failures:
        message = (
            "Some DTD relation types are not present in wn.constants "
            "(or DTDs were not parsed correctly):\n\n"
            + "\n\n".join(failures)
        )
        raise AssertionError(message)
