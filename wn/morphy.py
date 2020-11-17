
"""
Wordnet Morphy implementation
"""

import re
from typing import Dict, Generator, Iterable, Iterator, Optional

from wn._db import find_entries
from wn.constants import NOUN, VERB, ADJ

DETACHMENT_RULES = {
    NOUN: [ # Can be converted to a dict if Python 3.7+ is guaranteed
        ("s", ""),
        ("ses", "s"),
        ("xes", "x"),
        ("zes", "z"),
        ("ches", "ch"),
        ("shes", "sh"),
        ("men", "man"),
        ("ies", "y"),
    ],
    VERB: [
        ("s", ""),
        ("ies", "y"),
        ("es", "e"),
        ("es", ""),
        ("ed", "e"),
        ("ing", "e"),
        ("ing", ""),
    ],
    ADJ: [
        ("er", ""),
        ("est", ""),
        ("er", "e"),
        ("est", "e"),
    ]
}

PREPOSITIONS = ["about", "above", "across", "after", "among", "around", "athwart", 
                "at", "before", "behind", "below", "beneath", "beside", "besides", 
                "between", "betwixt", "beyond", "but", "by", "during", "except", 
                "for", "from", "into", "in", "near", "off", "of", "onto", "on", 
                "out", "over", "since", "till", "to", "under", "until", "unto", 
                "upon", "with"]

def expand_regex_rules(rules: dict) -> dict:
    xms = re.VERBOSE | re.MULTILINE | re.DOTALL
    RECURSE_GROUPED = re.compile(r"""
          (?P<any>   \(ANY\)   )
        | (?P<sing>  \(SING\)  )
        | (?P<plur>  \(PL\)    )
        | (?P<prep>  \(PREP\)  )
    """, flags=xms)
    
    regex_rules = {}

    for plural, singular in rules.items():
        plural_matches = RECURSE_GROUPED.finditer(plural)
        singular_matches = RECURSE_GROUPED.finditer(singular)

        for i, (plural_match, singular_match) in enumerate(zip(plural_matches, singular_matches)):
            # Case 1: Accept non-empty, and recursively call morphy on substring for lemmatization
            if plural_match.group() == "(PL)" and singular_match.group() == "(SING)":
                plural = RECURSE_GROUPED.sub(f"(?P<rec{i}>.+)", plural, count = 1)
            
            # Case 2: Accept only if preposition, and do not change on lemmatization.
            elif plural_match.group() == "(PREP)" and singular_match.group() == "(PREP)":
                plural = RECURSE_GROUPED.sub(f"(?P<prep{i}>{'|'.join(PREPOSITIONS)})", plural, count = 1)
            
            # Case 3: Accept non-empty, and do not change on lemmatization.
            elif plural_match.group() == "(ANY)" and singular_match.group() == "(ANY)":
                plural = RECURSE_GROUPED.sub(f"(?P<any{i}>.+)", plural, count = 1)
            
            else:
                raise Exception(f"Incorrect morphy rule: {plural!r} -> {singular!r}")
            singular = RECURSE_GROUPED.sub("{}", singular, count = 1)
        
        regex_rules[plural] = singular
    return regex_rules

def compile_rules(rule: dict) -> dict:
    return {compile_rule(plural): singular for plural, singular in rule.items()}

def compile_rule(rule: str) -> re.Pattern:
    return re.compile(rule, flags=re.IGNORECASE)

HYPHENATED_RULES = expand_regex_rules({
    "sons-of-(PL)":        "son-of-a-(SING)",     # sons-of-guns      -> son-of-a-gun
    "(PL)-(PREP)-(ANY)":   "(SING)-(PREP)-(ANY)", # mothers-in-law    -> mother-in-law
    "(PREP)-(PL)":         "(PREP)-(SING)",       
    "(PL)-errant":         "(SING)-errant",       # knights-errant    -> knight-errant
    "(PL)-(PREP)":         "(SING)-(PREP)",       # passers-by        -> passer-by
    "(PL)-general":        "(SING)-general"
})

COLLOCATION_RULES = expand_regex_rules({
    "(PREP) them":         "(PREP) it",           # Only works for "on them" and "to them"
    "(ANY)star generals":  "(ANY)star general",
})

# Add all rules from hyphenated, but with the dash replaced with a space.
COLLOCATION_RULES.update({
    plural.replace("-", " "): lemma.replace("-", " ") for plural, lemma in HYPHENATED_RULES.items()
})

FUL_RULES = expand_regex_rules({
    "(PL)ful": "(SING)ful"
})

# Turn left-hand-side into compiled regex
HYPHENATED_RULES = compile_rules(HYPHENATED_RULES)
COLLOCATION_RULES = compile_rules(COLLOCATION_RULES)
FUL_RULES = compile_rules(FUL_RULES)

WHITESPACE = compile_rule(r"(?P<before>\s*)(?P<word>.*?)(?P<after>\s*)")

# Combine all rules
# ALL_RULES = {**HYPHENATED_RULES, **COLLOCATION_RULES, **FUL_RULES}

"""
class LazyList:
    def __init__(self, gen: Generator) -> None:
        self.gen = gen
        self.cache = []
    
    def __getitem__(self, i: int):
        if i < 0:
            raise IndexError("Index cannot be negative.")

        self.fill_cache(i)
        return self.cache[i]
    
    def fill_cache(self, i: int):
        try:
            while len(self.cache) <= i:
                self.cache.append(next(self.gen))
        except StopIteration:
            raise IndexError

def expand_gen(options: Iterable[Iterable[str]]) -> Iterable[Iterable[str]]:
    for sublemmas in _expand_gen([LazyList(option) for option in options]):
        yield sublemmas
"""

def morphy(word: str, pos: str, strip:bool = False) -> Generator[str, None, None]:
    """
    These are cases to consider:
    - Hyphenation (mother-in-law)
    - Collacations (eat out, car pool, attorneys general)
    - Single words ending in -ful
    - Single words not ending in -ful
    - 

    TODO: Preserve capitalisation in some way.
    TODO: Consider replacing `strip` with `preserve_whitespace`.
    TODO: Currently, when recursing for subwords in collacations and hypenations, all subwords must
        : be the same POS as the combined word. This should be changed.
        : "asking for troubles" fails as morphy("troubles", wn.VERB) -> []

    # This is where we would check exceptions
    """

    def expand_gen(options: Iterable[Iterable[str]]) -> Iterable[Iterable[str]]:
        """
        Sub-iterators may not be infinite.
        Get all combinations of values.

            >>> list(expand_gen([1, 2, 3],
                                [4, 5],
                                [6, 7, 8]))
            [
                [1, 4, 6], [2, 4, 6], [3, 4, 6], 
                [1, 5, 6], [2, 5, 6], [3, 5, 6], 
                [1, 4, 7], [2, 4, 7], [3, 4, 7], 
                [1, 5, 7], [2, 5, 7], [3, 5, 7], 
                [1, 4, 8], [2, 4, 8], [3, 4, 8], 
                [1, 5, 8], [2, 5, 8], [3, 5, 8]
            ]
        """
        if not options:
            yield []
            return

        # Heads may not be a generator as it will be empty on the 
        # second iteration of the body of the `for tail ...` loop
        heads = list(options[0])
        for tail in expand_gen(options[1:]):
            for head in heads:
                yield [head] + tail

    def try_rules(word: str, rules: Dict[re.Pattern, str]) -> Generator[str, None, None]:
        """
        Try all rules from `rules` on word. 
        Yield all found lemmas
        """
        for pattern in rules:
            match = pattern.fullmatch(word)
            if match:
                lemma_format = rules[pattern]
                
                options = []
                # Requires Python 3.7 to ensure order of dict items
                for match_key, subword in match.groupdict().items():
                    if match_key.startswith("rec"):
                        options.append(morphy(subword, pos))
                    else:
                        options.append([subword])

                for option in expand_gen(options):
                    yield lemma_format.format(*option)
                # NOTE: If rules are no longer mutually exclusive, 
                # and multiple rules should be allowed to match per 
                # input word, this `return` should be remove.
                return

    def reapply_whitespace(lemma: str, match: re.Match, strip: bool) -> str:
        if strip:
            return lemma
        return match.group("before") + lemma + match.group("after")

    yielded_lemmas = []

    def in_wordnet(lemma: str, pos: str) -> bool:
        try:
            next(find_entries(form=lemma, pos=pos))
            return True
        except StopIteration:
            return False

    def yielded_previously(lemma: str) -> bool:
        return lemma in yielded_lemmas

    def no_yields() -> bool:
        return len(yielded_lemmas) == 0

    # Step 1: Extract whitespace before and after word
    ws_match = WHITESPACE.fullmatch(word)
    word = ws_match.group("word")

    # Step 2: Hyphenated phrases (mother-in-law)
    if "-" in word:
        for lemma in try_rules(word, HYPHENATED_RULES):
            if not yielded_previously(lemma) and in_wordnet(lemma, pos):
                yielded_lemmas.append(lemma)
                yield reapply_whitespace(lemma, ws_match, strip)

    # Step 3: Collacations (eat out, on them)
    if " " in word:
        for lemma in try_rules(word, COLLOCATION_RULES):
            if not yielded_previously(lemma) and in_wordnet(lemma, pos):
                yielded_lemmas.append(lemma)
                yield reapply_whitespace(lemma, ws_match, strip)
        
        # Step 3.1: If none of those matched, recurse with all subwords
        if no_yields():
            for sublemmas in expand_gen([morphy(subword, pos) for subword in word.split()]):
                lemma = " ".join(sublemmas)
                
                if not yielded_previously(lemma) and in_wordnet(lemma, pos):
                    yielded_lemmas.append(lemma)
                    yield reapply_whitespace(lemma, ws_match, strip)

    # Step 4: -ful (wonderful)
    if word.lower().endswith("ful"):
        for lemma in try_rules(word, FUL_RULES):
            if not yielded_previously(lemma) and in_wordnet(lemma, pos):
                yielded_lemmas.append(lemma)
                yield reapply_whitespace(lemma, ws_match, strip)

    # Step 5: Remaining options, single words
    for suffix, replacement in DETACHMENT_RULES[pos]:
        if word.endswith(suffix):
            lemma = word[:-len(suffix)] + replacement

            if not yielded_previously(lemma) and in_wordnet(lemma, pos):
                yielded_lemmas.append(lemma)
                yield reapply_whitespace(lemma, ws_match, strip)

    # Step 6: Periods in word, when no exact match was found
    if "." in word and no_yields():
        for lemma in morphy(word.replace(".", ""), pos):
            # The standard checks should not be required as there are
            # no yields yet, and morphy shouldn't yield values not
            # in wordnet, nor duplicates.
            # if not yielded_previously(lemma):# and in_wordnet(lemma, pos):
            yielded_lemmas.append(lemma)
            yield reapply_whitespace(lemma, ws_match, strip)

    # Step 7: Yield the input word if it's already in Wordnet
    if not yielded_previously(word) and in_wordnet(word, pos):
        yielded_lemmas.append(word)
        yield reapply_whitespace(word, ws_match, strip)

__all__ = [
    "morphy"
]
