# Wikidata Lexemes

Our multilingual wordnet covers nouns, verbs, adjectives, and adverbs well, but lacks function words (prepositions, conjunctions, determiners, pronouns, etc.).

This module creates Global WordNet LMF extension files using Wikidata Lexemes to fill that gap.

## Setup

Install dependencies:

```bash
pip install ijson requests tqdm
```

Download the lexemes dump (~400MB):

```bash
curl -O https://dumps.wikimedia.org/wikidatawiki/entities/latest-lexemes.json.bz2
```

## Usage

Run the extension generator:

```bash
python create_extensions.py
```

This will:
1. Filter lexemes to exclude nouns, verbs, adjectives, adverbs, and phrases
2. Build an interlingual index (ILI) linking senses across languages via English
3. For lexemes with no Wikidata senses, fall back to the English Wiktionary REST API (filters out reference-only definitions, onomatopoeia, dialectal/archaic terms not covered by omw-en)
4. Generate XML extension files in `output/` for each language

Set `LANG_FILTER=en` to restrict generation to a single language while iterating.

### Caching

Web requests are cached on disk under `extras/` (gitignored):
- `extras/wikidata/` — POS/language Q-code metadata
- `extras/wiktionary/` — Wiktionary REST `definition` responses
- `extras/wiktionary-cats/` — Wiktionary page categories (action API)

To force a refresh of a cached entry, delete the corresponding file.

## Output

The script generates ~130 language-specific XML files in Global WordNet LMF format:
- `extensions/en.xml` - English
- `extensions/de.xml` - German
- `extensions/ja.xml` - Japanese
- etc.

Each file contains lexical entries with:
- Lemma and part of speech (short WN-LMF codes — `h` pronoun, `d` determiner, `m` numeral, `i` interjection, `q` interrogative, `y` particle, plus the existing `n/v/a/r/s/t/c/p/x`)
- Sense definitions and glosses
- Usage examples (where available)
- Sense relations (synonyms, antonyms, hypernyms, hyponyms)
- "Interlingual index" like links to English senses

## Loading into the database

`wn.add(file.xml)` stores an extension as a separate lexicon. To get one
lexicon per language instead, use the bundled merge utility:

```bash
python merge_extension.py output/*.xml
```

It calls `wn.add` and then rewrites the database so the extension's
entries, senses and synsets belong to the base lexicon (e.g. `omw-en:1.4`),
and deletes the now-empty extension lexicon row. See
[goodmami/wn#304](https://github.com/goodmami/wn/issues/304) for context.
