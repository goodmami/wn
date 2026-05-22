"""Cached Wikidata entity fetcher (used to resolve POS/language Q-codes)."""
import json
import re
from collections.abc import Callable
from functools import cache
from pathlib import Path

import requests

EXTRAS_DIR = Path(__file__).parent / "extras" / "wikidata"
USER_AGENT = (
    "WikidataLexemesBot/1.0 "
    "(https://github.com/sign-language-processing/dictionary)"
)


def safe_filename(name: str, max_len: int = 80) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)[:max_len] or "_"


def cached_json_fetch(path: Path, fetch: Callable[[], dict]) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        pass
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


@cache
def fetch_wikidata_entity(q_code: str) -> dict:
    def _fetch():
        url = f"https://www.wikidata.org/wiki/Special:EntityData/{q_code}.json"
        response = requests.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=30,
        )
        response.raise_for_status()
        return response.json()

    data = cached_json_fetch(EXTRAS_DIR / f"{q_code}.json", _fetch)
    entities = data["entities"]
    return entities.get(q_code) or next(iter(entities.values()))


@cache
def get_label(q_code: str) -> str:
    entity = fetch_wikidata_entity(q_code)
    labels = entity.get("labels", {})
    if "en" in labels:
        return labels["en"]["value"].lower()
    if labels:
        return next(iter(labels.values()))["value"].lower()
    return q_code


@cache
def get_language_iso(q_code: str) -> str | None:
    entity = fetch_wikidata_entity(q_code)
    iso_claim = entity.get("claims", {}).get("P218", [])
    if iso_claim:
        datavalue = iso_claim[0].get("mainsnak", {}).get("datavalue")
        if datavalue:
            return datavalue["value"]
    return None
