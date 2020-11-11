
import math

import wn
from wn._core import Synset


def path(synset1, synset2):
    """Return the Path similarity of *synset1* and *synset2*."""
    distance = len(synset1.shortest_path(synset2, simulate_root=True))
    return 1 / (distance + 1)


def wup(synset1: Synset, synset2: Synset) -> float:
    """Return the Wu-Palmer similarity of *synset1* and *synset2*."""
    lch = synset1.lowest_common_hypernyms(synset2, simulate_root=True)[0]
    n = lch.max_depth() + 1
    n1 = len(synset1.shortest_path(lch, simulate_root=True))
    n2 = len(synset2.shortest_path(lch, simulate_root=True))
    return (2 * n) / (n1 + n2 + 2 * n)


def lch(synset1: Synset, synset2: Synset, max_depth: int = 0) -> float:
    """Return the Leacock-Chodorow similarity of *synset1* and *synset2*."""
    distance = len(synset1.shortest_path(synset2, simulate_root=True))
    if max_depth <= 0:
        raise wn.Error('max_depth must be greater than 0')
    return -math.log((distance + 1) / (2 * max_depth))
