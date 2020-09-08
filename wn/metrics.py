
from wn._core import Word, Synset


# Word-based Metrics

def ambiguity(word: Word) -> int:
    return len(word.synsets())


def average_ambiguity(synset: Synset) -> float:
    words = synset.words()
    return sum(len(word.synsets()) for word in words) / len(words)
