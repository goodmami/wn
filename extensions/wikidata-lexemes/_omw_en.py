"""Cached omw-en lemma → POS coverage."""
from functools import cache


@cache
def omw_en_pos() -> dict[str, frozenset[str]]:
    """Return {lemma_lower: frozenset of WN POSes}. Empty if omw-en unavailable."""
    try:
        import wn
        en = wn.Wordnet(lexicon="omw-en")
    except Exception:
        return {}
    by_lemma: dict[str, set[str]] = {}
    for word in en.words():
        for form in (word.lemma(), *word.forms()):
            by_lemma.setdefault(form.lower(), set()).add(word.pos)
    return {lemma: frozenset(pos) for lemma, pos in by_lemma.items()}
