#!/usr/bin/env python3
import bz2
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple
from xml.sax.saxutils import escape as xml_escape

import ijson
from _omw_en import omw_en_pos
from _pos_map import CONTENT_POS_MAP, POS_MAP
from _wikidata import get_label, get_language_iso
from _wiktionary import (
    fetch_wiktionary,
    is_quality_lemma,
    prefetch_categories_batch,
    wiktionary_definition,
)
from tqdm import tqdm

from wn.constants import OTHER

LANG_FILTER = os.environ.get("LANG_FILTER", "").strip() or None
DATA_PATH = Path(__file__).parent / "latest-lexemes.json.bz2"
EXTENSIONS_DIR = Path(__file__).parent / "output"

SKIP_POS = frozenset({
    # Covered in WordNet already
    "noun",
    "proper noun",
    "verb",
    "proper verb",  # to Zoom, to Google
    "phrasal verb",  # get over, find out
    "adverb",
    "adjective",
    "satellite adjective",
    "proper adjective",
    # Subword, less useful for us
    "prefix",
    "suffix",
    "interfix",
    "adjectival suffix",
    "nominal suffix",
    "verbal suffix",
    "adverbial suffix",
    "combining form",
    "postpositive adjective",
    "digraph",  # two letters representing one sound
    "contraction",
    "letter",
    "name suffix",
    "symbol",
    # Phrases
    "phrase",
    "saying",
    "idiom",
    "proverb",
    "everyday collocation",
    "interjectional locution",
    "formulaic language",
    "verbal locution",
    "prepositional syntagma",
    "phrasal template",
    "adjectival phrase",
    "noun phrase",
    "verb phrase",
    "nominal locution",
    "multiword expression",
    "conjunctive locution",
    "conjunctive adverb",
    "collocation",
    "attributive locution",
    "slogan",
    # Entities
    "initialism",
    "demonym",
    "national demonym",
    "toponym",
})

SENSE_RELATIONS = {
    "P5973": "similar",   # synonym
    "P5974": "antonym",   # antonym
    "P5975": "hyponym",   # troponym of (more specific)
    "P6593": "hypernym",  # hyperonym (more general)
}

ENGLISH_LANG_Q = "Q1860"
MODAL_VERB_Q = "Q560570"  # P31 value — lexemes the dictionary should always cover

# Wikidata grammatical-feature Q-codes that disqualify a form from emission.
NEGATION_Q = "Q1478451"
_SKIP_FORM_FEATURES = frozenset({NEGATION_Q})


def _has_p31(lex: dict, target_q: str) -> bool:
    for claim in lex.get("claims", {}).get("P31", []):
        dv = claim.get("mainsnak", {}).get("datavalue")
        if (dv and dv.get("type") == "wikibase-entityid"
                and dv["value"]["id"] == target_q):
            return True
    return False

# Languages whose omw lexicon ID isn't `omw-<lang>`.
_BASE_LEXICON_OVERRIDES = {"de": ("odenet", "1.4")}


def _escape(text: str) -> str:
    return xml_escape(text, {'"': "&quot;", "'": "&apos;"})


def _stream_lexemes():
    with bz2.open(DATA_PATH, "rb") as f:
        yield from ijson.items(f, "item")


def _has_relation_to_kept(lex: dict, kept_sense_ids: set[str]) -> bool:
    for sense in lex.get("senses", []):
        for prop in SENSE_RELATIONS:
            for claim in sense.get("claims", {}).get(prop, []):
                dv = claim.get("mainsnak", {}).get("datavalue")
                if (dv and dv.get("type") == "wikibase-entityid"
                        and dv["value"]["id"] in kept_sense_ids):
                    return True
    return False


# POS labels that even the content-gap escape should never resurrect.
# Brand names, place names, and people belong in encyclopaedias, not dictionaries.
_NEVER_GAP_FILL = frozenset({"proper noun", "proper verb", "proper adjective"})


def _is_english_content_gap(lex: dict, pos_name: str) -> bool:
    """English-only escape: a SKIP_POS-classified content-POS lemma stays in if
    omw-en lacks it under that same POS. Skips proper-noun-derived lemmas
    (any capitalised lemma, initialism, etc.) — those belong to encyclopaedic
    rather than dictionary scope."""
    if lex.get("language") != ENGLISH_LANG_Q:
        return False
    if pos_name in _NEVER_GAP_FILL:
        return False
    wn_pos = CONTENT_POS_MAP.get(pos_name)
    if not wn_pos:
        return False
    raw_lemma = lex.get("lemmas", {}).get("en", {}).get("value", "")
    if not raw_lemma or raw_lemma[0].isupper():
        return False
    return wn_pos not in omw_en_pos().get(raw_lemma.lower(), frozenset())


def filter_lexemes() -> tuple[list[dict], set[tuple[str, str]]]:
    """Stream the dump once. Keep lexemes whose POS isn't in SKIP_POS — with
    one exception: English content-POS lemmas that omw-en doesn't already
    have are kept (filling the gap). Abbreviations are buffered and kept
    only if they have a sense relation to a kept sense.

    Dedupe by (lang_iso, lemma, pos_code) so downstream sense-relation targets
    can't dangle: if a duplicate lexeme is dropped here, its sense IDs are
    excluded from `kept_lang_senses` too.
    """
    print("Step 1: Filtering lexemes...")
    kept_sense_ids: set[str] = set()
    kept_lang_senses: set[tuple[str, str]] = set()
    seen_lemma_pos: set[tuple[str, str, str]] = set()
    filtered: list[dict] = []
    pending_abbrev: list[dict] = []

    def _try_keep(lex: dict, pos_name: str) -> bool:
        lemmas = lex.get("lemmas", {})
        if not lemmas:
            return False
        # English-only: skip lexemes Wikidata hasn't cross-referenced against
        # any dictionary (no claims at all) — those are usually niche slang.
        if lex.get("language") == ENGLISH_LANG_Q and not lex.get("claims"):
            return False
        pos_code = POS_MAP.get(pos_name, OTHER)
        accepted_for_any_lang = False
        for lang_iso, lemma_obj in lemmas.items():
            lemma = lemma_obj.get("value", "")
            # Multi-word lemmas that start with uppercase are usually
            # proper-noun-derived (e.g. "Jesus Christ", "God bless you").
            if " " in lemma and lemma[:1].isupper():
                continue
            key = (lang_iso, lemma, pos_code)
            if key in seen_lemma_pos:
                continue
            seen_lemma_pos.add(key)
            accepted_for_any_lang = True
            for sense in lex.get("senses", []):
                kept_sense_ids.add(sense["id"])
                kept_lang_senses.add((lang_iso, sense["id"]))
        return accepted_for_any_lang

    for lex in tqdm(_stream_lexemes(), desc="Streaming"):
        pos_q = lex.get("lexicalCategory")
        if not pos_q:
            continue
        pos_name = get_label(pos_q)
        if pos_name == "abbreviation":
            pending_abbrev.append(lex)
            continue
        if pos_name in SKIP_POS:
            keep_for_modal = (
                lex.get("language") == ENGLISH_LANG_Q
                and _has_p31(lex, MODAL_VERB_Q)
            )
            if not keep_for_modal and not _is_english_content_gap(lex, pos_name):
                continue
        if _try_keep(lex, pos_name):
            filtered.append(lex)

    for lex in pending_abbrev:
        if _has_relation_to_kept(lex, kept_sense_ids):
            pos_name = get_label(lex["lexicalCategory"])
            if _try_keep(lex, pos_name):
                filtered.append(lex)

    print(f"  Kept {len(filtered)} lexemes, {len(kept_lang_senses)} sense pairs")
    return filtered, kept_lang_senses


def _build_ili_index(lexemes: list[dict]) -> dict[str, str]:
    print("Step 2: Building ILI index...")
    english_senses: set[str] = set()
    translations: dict[str, list[str]] = {}
    for lexeme in tqdm(lexemes, desc="Indexing"):
        is_english = lexeme.get("language") == ENGLISH_LANG_Q
        for sense in lexeme.get("senses", []):
            sense_id = sense["id"]
            if is_english:
                english_senses.add(sense_id)
            for claim in sense.get("claims", {}).get("P5972", []):
                dv = claim.get("mainsnak", {}).get("datavalue")
                if dv and dv.get("type") == "wikibase-entityid":
                    translations.setdefault(sense_id, []).append(dv["value"]["id"])

    ili_index: dict[str, str] = {sense_id: sense_id.lower() for sense_id in english_senses}
    for sense_id, targets in translations.items():
        if sense_id in ili_index:
            continue
        for target in targets:
            if target in english_senses:
                ili_index[sense_id] = target.lower()
                break

    print(f"  English senses: {len(english_senses)}")
    print(f"  Senses with ILI: {len(ili_index)}")
    return ili_index


class NormalizedSense(NamedTuple):
    id: str
    gloss: str
    examples: list[str]
    relations_xml: list[str]


def _pick_gloss(glosses: dict, lang_iso: str) -> str:
    for candidate in (lang_iso, "en"):
        text = glosses.get(candidate, {}).get("value", "")
        if text:
            return text
    for entry in glosses.values():
        text = entry.get("value", "")
        if text:
            return text
    return ""


def _extract_sense_examples(lexeme: dict, lang_iso: str) -> dict[str, list[str]]:
    sense_examples: dict[str, list[str]] = {}
    for claim in lexeme.get("claims", {}).get("P5831", []):
        dv = claim.get("mainsnak", {}).get("datavalue")
        if not dv or dv.get("type") != "monolingualtext":
            continue
        text_value = dv.get("value", {})
        if text_value.get("language") != lang_iso:
            continue
        example_text = text_value.get("text", "")
        for qual in claim.get("qualifiers", {}).get("P6072", []):
            qual_dv = qual.get("datavalue")
            if qual_dv and qual_dv.get("type") == "wikibase-entityid":
                sense_examples.setdefault(qual_dv["value"]["id"], []).append(example_text)
    return sense_examples


def _sense_relations_xml(
    sense: dict, lang_iso: str, kept_lang_senses: set[tuple[str, str]],
) -> list[str]:
    relations = []
    for prop, rel_type in SENSE_RELATIONS.items():
        for claim in sense.get("claims", {}).get(prop, []):
            dv = claim.get("mainsnak", {}).get("datavalue")
            if not (dv and dv.get("type") == "wikibase-entityid"):
                continue
            target_id = dv["value"]["id"]
            if (lang_iso, target_id) not in kept_lang_senses:
                continue
            target_synset = f"wikidata-{lang_iso}-{target_id}"
            relations.append(
                f'        <SenseRelation relType="{rel_type}" target="{target_synset}"/>'
            )
    return relations


_LEADING_APOS = "'’ʼ‘"  # ASCII, curly right, modifier-letter, curly left


def _extract_alt_forms(lexeme: dict, lang_iso: str, main_lemma: str) -> list[str]:
    """Return alternative form spellings for this lexeme in `lang_iso`,
    excluding the main lemma, negation forms, and apostrophe-leading
    contractions (`'ll`, `'d`, `'s`, ...)."""
    out: list[str] = []
    seen = {main_lemma}
    for form in lexeme.get("forms", []):
        if any(f in _SKIP_FORM_FEATURES for f in form.get("grammaticalFeatures", [])):
            continue
        rep = form.get("representations", {}).get(lang_iso, {}).get("value")
        if not rep or rep in seen:
            continue
        if rep[0] in _LEADING_APOS:
            continue
        seen.add(rep)
        out.append(rep)
    return out


def _normalized_senses(
    lexeme: dict, lemma: str, pos_name: str, lang_iso: str,
    kept_lang_senses: set[tuple[str, str]],
) -> list[NormalizedSense]:
    raw = lexeme.get("senses", [])
    if raw:
        sense_examples = _extract_sense_examples(lexeme, lang_iso)
        return [
            NormalizedSense(
                id=sense["id"],
                gloss=_pick_gloss(sense.get("glosses", {}), lang_iso),
                examples=sense_examples.get(sense["id"], []),
                relations_xml=_sense_relations_xml(sense, lang_iso, kept_lang_senses),
            )
            for sense in raw
        ]
    if not lemma or len(lemma) > 80:
        return []
    result = wiktionary_definition(
        lemma, pos_name, lang_iso,
        bypass_archaic=_has_p31(lexeme, MODAL_VERB_Q),
    )
    if not result:
        return []
    definition, examples = result
    return [NormalizedSense(
        id=f"{lexeme['id']}-WKT1",
        gloss=definition,
        examples=examples,
        relations_xml=[],
    )]


def build_xml_entry(
    lexeme: dict, lang_iso: str,
    ili_index: dict[str, str],
    kept_lang_senses: set[tuple[str, str]],
) -> tuple[str, list[str], str, str] | None:
    """Return (entry_xml, synset_xml_list, lemma, pos_code) or None."""
    lemmas = lexeme.get("lemmas", {})
    if lang_iso not in lemmas:
        return None
    lemma = lemmas[lang_iso]["value"]

    pos_q = lexeme.get("lexicalCategory")
    if not pos_q:
        return None
    pos_name = get_label(pos_q)
    pos_code = POS_MAP.get(pos_name, OTHER)

    senses = _normalized_senses(lexeme, lemma, pos_name, lang_iso, kept_lang_senses)
    if not senses:
        return None

    sense_entries = []
    synset_entries = []
    for sense in senses:
        synset_id = f"wikidata-{lang_iso}-{sense.id}"
        ili = ili_index.get(sense.id, synset_id)

        sense_content = (
            f'      <Sense id="{sense.id}"'
            f' synset="{synset_id}" ili="{ili}">\n'
            f'        <Definition>{_escape(sense.gloss)}</Definition>\n'
        )
        for example in sense.examples:
            sense_content += f'        <Example>{_escape(example)}</Example>\n'
        if sense.relations_xml:
            sense_content += "\n".join(sense.relations_xml) + "\n"
        sense_content += "      </Sense>"
        sense_entries.append(sense_content)

        synset_content = (
            f'    <Synset id="{synset_id}" ili="{ili}" partOfSpeech="{pos_code}">\n'
            f'      <Definition>{_escape(sense.gloss)}</Definition>\n'
        )
        for example in sense.examples:
            synset_content += f'      <Example>{_escape(example)}</Example>\n'
        synset_content += "    </Synset>"
        synset_entries.append(synset_content)

    alt_forms = _extract_alt_forms(lexeme, lang_iso, lemma)
    form_lines = "".join(
        f'      <Form writtenForm="{_escape(form)}"/>\n' for form in alt_forms
    )
    entry_xml = (
        f'    <LexicalEntry id="{lexeme["id"]}">\n'
        f'      <Lemma writtenForm="{_escape(lemma)}" partOfSpeech="{pos_code}"/>\n'
        + form_lines
        + "\n".join(sense_entries)
        + "\n    </LexicalEntry>"
    )
    return entry_xml, synset_entries, lemma, pos_code


def _xml_header(lang_iso: str) -> str:
    base_id, base_version = _BASE_LEXICON_OVERRIDES.get(
        lang_iso, (f"omw-{lang_iso}", "1.4"),
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE LexicalResource SYSTEM "https://globalwordnet.github.io/schemas/WN-LMF-1.4.dtd">
<LexicalResource xmlns:dc="https://globalwordnet.github.io/schemas/dc/">
  <LexiconExtension id="wikidata-{lang_iso}"
                    label="Wikidata {lang_iso.upper()} Lexemes Extension"
                    language="{lang_iso}"
                    email="amit@nagish.com"
                    license="https://creativecommons.org/publicdomain/zero/1.0/"
                    version="1.0">
    <Extends id="{base_id}" version="{base_version}"/>
'''


_XML_FOOTER = """  </LexiconExtension>
</LexicalResource>
"""


def _wiktionary_task(lex: dict) -> tuple[str, str] | None:
    if lex.get("senses"):
        return None
    lang_q = lex.get("language")
    if not lang_q:
        return None
    lang_iso = get_language_iso(lang_q)
    if not lang_iso or (LANG_FILTER and lang_iso != LANG_FILTER):
        return None
    lemma_obj = lex.get("lemmas", {}).get(lang_iso)
    if not lemma_obj:
        return None
    lemma = lemma_obj["value"]
    if not is_quality_lemma(lemma):
        return None
    return (lemma, lang_iso)


def prefetch_wiktionary(lexemes: list[dict]) -> None:
    tasks = sorted({task for lex in lexemes if (task := _wiktionary_task(lex))})
    if not tasks:
        return
    print(f"Pre-fetching {len(tasks)} Wiktionary entries...")
    with ThreadPoolExecutor(max_workers=16) as executor:
        list(tqdm(
            executor.map(lambda t: fetch_wiktionary(*t), tasks),
            total=len(tasks), desc="Wiktionary defs",
        ))

    en_lemmas = [lemma for lemma, iso in tasks if iso == "en"]
    if en_lemmas:
        print(f"Pre-fetching categories for {len(en_lemmas)} EN lemmas...")
        prefetch_categories_batch(en_lemmas, "en")


def write_all_extensions(
    lexemes: list[dict],
    ili_index: dict[str, str],
    kept_lang_senses: set[tuple[str, str]],
) -> None:
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)

    file_handlers: dict[str, object] = {}
    entry_counts: dict[str, int] = {}
    synsets_by_lang: dict[str, list[str]] = {}

    print("Step 3: Writing all language extensions...")
    try:
        for lexeme in tqdm(lexemes, desc="Writing"):
            lang_q = lexeme.get("language")
            if not lang_q:
                continue
            lang_iso = get_language_iso(lang_q)
            if not lang_iso:
                continue
            if LANG_FILTER and lang_iso != LANG_FILTER:
                continue

            result = build_xml_entry(lexeme, lang_iso, ili_index, kept_lang_senses)
            if not result:
                continue
            entry, synsets, lemma, pos_code = result

            handler = file_handlers.get(lang_iso)
            if handler is None:
                output_path = EXTENSIONS_DIR / f"{lang_iso}.xml"
                handler = open(output_path, "w", encoding="utf-8")  # noqa: SIM115
                handler.write(_xml_header(lang_iso))
                file_handlers[lang_iso] = handler
                entry_counts[lang_iso] = 0
                synsets_by_lang[lang_iso] = []

            handler.write(entry + "\n")
            synsets_by_lang[lang_iso].extend(synsets)
            entry_counts[lang_iso] += 1
    finally:
        for lang_iso, handler in file_handlers.items():
            for synset in synsets_by_lang.get(lang_iso, []):
                handler.write(synset + "\n")
            handler.write(_XML_FOOTER)
            handler.close()

    print(f"  Wrote {len(file_handlers)} language files:")
    for lang_iso in sorted(entry_counts):
        print(f"    {lang_iso}: {entry_counts[lang_iso]} entries")


def main() -> None:
    lexemes, kept_lang_senses = filter_lexemes()
    ili_index = _build_ili_index(lexemes)
    prefetch_wiktionary(lexemes)
    write_all_extensions(lexemes, ili_index, kept_lang_senses)


if __name__ == "__main__":
    main()
