"""Wiktionary REST fallback for Wikidata Lexemes that lack senses."""
import html
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path

import requests

from _omw_en import omw_en_pos
from _wikidata import USER_AGENT, cached_json_fetch, safe_filename

_EXTRAS = Path(__file__).parent / "extras"
CACHE_DIR = _EXTRAS / "wiktionary"
CATS_DIR = _EXTRAS / "wiktionary-cats"

# "<Lang> <fragment> terms" tags the whole word as that flavor (e.g.
# "English archaic terms" — the entire term is archaic). The looser
# "<Lang> terms with <fragment> senses" tag matches plenty of modern
# multi-sense words and is unsafe as a hard filter on its own.
_OLD_FRAGMENTS = (
    "archaic", "obsolete", "dated", "poetic", "literary",
)
_ALWAYS_EXCLUDE_FRAGMENTS = (
    "onomatopoeia", "dialectal", "internet slang", "eye dialect",
)

WD_TO_WKT_POS: dict[str, tuple[str, ...]] = {
    "pronoun": ("Pronoun",),
    "personal pronoun": ("Pronoun",),
    "reflexive pronoun": ("Pronoun",),
    "reflexive personal pronoun": ("Pronoun",),
    "reciprocal pronoun": ("Pronoun",),
    "interrogative pronoun": ("Pronoun",),
    "indefinite pronoun": ("Pronoun",),
    "relative pronoun": ("Pronoun",),
    "demonstrative pronoun": ("Pronoun",),
    "definite pronoun": ("Pronoun",),
    "subject pronoun": ("Pronoun",),
    "object pronoun": ("Pronoun",),
    "possessive determiner": ("Determiner", "Pronoun"),
    "determiner": ("Determiner", "Article"),
    "definite article": ("Article", "Determiner"),
    "indefinite article": ("Article", "Determiner"),
    "demonstrative determiner": ("Determiner",),
    "conjunction": ("Conjunction",),
    "coordinating conjunction": ("Conjunction",),
    "subordinating conjunction": ("Conjunction",),
    "concessive conjunction": ("Conjunction",),
    "interjection": ("Interjection",),
    "preposition": ("Preposition",),
    "postposition": ("Postposition", "Preposition"),
    "numeral": ("Numeral", "Number"),
    "number": ("Number", "Numeral"),
    "digit": ("Number", "Numeral"),
    "particle": ("Particle",),
    "infinitive marker": ("Particle",),
    "grammatical particle": ("Particle",),
    "interrogative word": ("Adverb", "Determiner", "Pronoun"),
    "adverb": ("Adverb",),
    "prepositional adverb": ("Adverb",),
    "interrogative adverb": ("Adverb",),
    "noun": ("Noun",),
    "agent noun": ("Noun",),
    "common noun": ("Noun",),
    "verb": ("Verb",),
    "auxiliary verb": ("Verb",),
    "adjective": ("Adjective",),
}


def _def_cache_path(lemma: str, lang_iso: str) -> Path:
    return CACHE_DIR / lang_iso / f"{safe_filename(lemma)}.json"


def _cats_cache_path(lemma: str, lang_iso: str) -> Path:
    return CATS_DIR / lang_iso / f"{safe_filename(lemma)}.json"


@cache
def fetch_wiktionary(lemma: str, lang_iso: str) -> dict | None:
    path = _def_cache_path(lemma, lang_iso)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data or None
    except FileNotFoundError:
        pass

    url = f"https://{lang_iso}.wiktionary.org/api/rest_v1/page/definition/{lemma}"
    try:
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=30,
        )
    except requests.RequestException:
        return None

    if response.status_code == 404:
        data = {}
    elif response.ok:
        try:
            data = response.json()
        except ValueError:
            data = {}
    else:
        # Transient (429, 5xx, ...) — don't cache; retry next run.
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data or None


@cache
def fetch_wiktionary_categories(lemma: str, lang_iso: str) -> list[str]:
    path = _cats_cache_path(lemma, lang_iso)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        pass
    result = _fetch_categories_batch([lemma], lang_iso)
    return result.get(lemma, [])


_thread_local = threading.local()


def _session() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update({"User-Agent": USER_AGENT})
        _thread_local.session = sess
    return sess


def _fetch_one_batch(
    batch: list[str], lang_iso: str,
) -> dict[str, list[str]]:
    url = f"https://{lang_iso}.wiktionary.org/w/api.php"
    session = _session()
    per_lemma: dict[str, list[str]] = {lemma: [] for lemma in batch}
    title_to_input: dict[str, str] = {lemma: lemma for lemma in batch}
    cont: dict[str, str] = {}
    succeeded = False

    while True:
        params = {
            "action": "query",
            "prop": "categories",
            "format": "json",
            "titles": "|".join(batch),
            "clshow": "!hidden",
            "cllimit": "max",
            "redirects": "1",
            **cont,
        }
        response = None
        for attempt in range(3):
            try:
                response = session.get(url, params=params, timeout=60)
            except requests.RequestException:
                time.sleep(1 + attempt)
                continue
            if response.status_code == 429:
                time.sleep(2 + 2 * attempt)
                continue
            break

        if response is None or not response.ok:
            break
        try:
            data = response.json()
        except ValueError:
            break

        succeeded = True
        for n in data.get("query", {}).get("normalized", []):
            title_to_input[n["to"]] = n["from"]
        for r in data.get("query", {}).get("redirects", []):
            title_to_input[r["to"]] = title_to_input.get(r["from"], r["from"])

        for page in data.get("query", {}).get("pages", {}).values():
            title = page.get("title")
            original = title_to_input.get(title, title)
            cats = [
                c["title"].replace("Category:", "")
                for c in page.get("categories", [])
            ]
            per_lemma.setdefault(original, []).extend(cats)

        cont_block = data.get("continue", {})
        if "clcontinue" in cont_block:
            cont = {"clcontinue": cont_block["clcontinue"]}
        else:
            break

    if not succeeded:
        return {}
    for lemma, cats in per_lemma.items():
        path = _cats_cache_path(lemma, lang_iso)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cats, f)
    return per_lemma


def _fetch_categories_batch(
    lemmas: list[str], lang_iso: str,
) -> dict[str, list[str]]:
    """Action API sums categories across all pages in one response under
    cllimit, so a single popular term (e.g. ``moo``, 60 cats) can starve the
    rest of its batch. Keep batches small and follow ``clcontinue`` pagination.
    Batches run in parallel."""
    if not lemmas:
        return {}
    batches = [lemmas[i:i + 5] for i in range(0, len(lemmas), 5)]
    out: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for partial in ex.map(lambda b: _fetch_one_batch(b, lang_iso), batches):
            out.update(partial)
    return out


def prefetch_categories_batch(lemmas: list[str], lang_iso: str) -> None:
    missing = [
        lemma for lemma in lemmas
        if not _cats_cache_path(lemma, lang_iso).exists()
    ]
    if missing:
        _fetch_categories_batch(missing, lang_iso)


def _is_archaic_en(lemma: str) -> bool:
    """Drop English lemmas Wiktionary tags as onomatopoeic/dialectal (always),
    or as archaic/obsolete/dated/poetic/literary AND omw-en doesn't carry them
    in current use under any POS."""
    cats = fetch_wiktionary_categories(lemma, "en")
    relevant = [c.lower() for c in cats if c.startswith("English ")]
    if any(any(f in c for f in _ALWAYS_EXCLUDE_FRAGMENTS) for c in relevant):
        return True
    if not any(any(f in c for f in _OLD_FRAGMENTS) for c in relevant):
        return False
    return lemma.lower() not in omw_en_pos()


_CSS_RULE = re.compile(r"\.[A-Za-z][\w\-]*(?:\s*\.[A-Za-z][\w\-]*)*\s*\{[^}]*\}")
_LEMMA_OK = re.compile(r"^[A-Za-z][A-Za-z'\-]*$")
_REFERENCE_PREFIXES = (
    "alternative form of", "alternative spelling of",
    "alternate form of", "alternate spelling of",
    "initialism of", "abbreviation of", "acronym of",
    "contraction of", "eye dialect of",
    "obsolete form of", "obsolete spelling of",
    "archaic form of", "archaic spelling of",
    "pronunciation spelling of",
    "synonym of", "plural of",
    "past tense of", "past participle of", "present participle of",
    "inflected form of", "misspelling of",
    "informal form of", "informal spelling of",
)
_SOUND_PATTERNS = (
    "used to indicate the sound",
    "used to represent the sound",
    "indicating the sound of",
    "imitating the sound",
    "representing the sound",
    "the characteristic sound",
    "the sound made by",
    "onomatopoeia",
)


def _strip(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = _CSS_RULE.sub("", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _is_reference_definition(definition: str) -> bool:
    lower = definition.lower().lstrip()
    return any(lower.startswith(p) for p in _REFERENCE_PREFIXES)


def _is_sound_definition(definition: str) -> bool:
    lower = definition.lower()
    return any(p in lower for p in _SOUND_PATTERNS)


def is_quality_lemma(lemma: str) -> bool:
    if not _LEMMA_OK.match(lemma):
        return False
    return not (lemma.isupper() and len(lemma) > 1)


def wiktionary_definition(
    lemma: str, wd_pos_label: str, lang_iso: str,
    *, bypass_archaic: bool = False,
) -> tuple[str, list[str]] | None:
    """Return (definition, examples) from Wiktionary for the lemma + POS."""
    if not is_quality_lemma(lemma):
        return None
    if lang_iso == "en" and not bypass_archaic and _is_archaic_en(lemma):
        return None

    data = fetch_wiktionary(lemma, lang_iso)
    if not data:
        return None

    entries = data.get(lang_iso) or data.get("en") or []
    if not entries:
        entries = next(iter(data.values()), [])

    acceptable = WD_TO_WKT_POS.get(wd_pos_label)
    if not acceptable:
        return None

    for entry in entries:
        if entry.get("partOfSpeech") not in acceptable:
            continue
        for defn in entry.get("definitions", []):
            definition = _strip(defn.get("definition", ""))
            if not definition or _is_reference_definition(definition):
                continue
            if _is_sound_definition(definition):
                continue
            examples = [_strip(e) for e in defn.get("examples", []) if _strip(e)]
            return definition, examples
    return None
