
"""Synset similarity metrics."""

import math

import wn
from wn._core import Synset


def path(synset1, synset2):
    """Return the Path similarity of *synset1* and *synset2*.

    Arguments:
        synset1: The first synset to compare.
        synset2: The second synset to compare.
        simulate_root: When :python:`True`, a fake root node connects
            all other roots; default: :python:`False`.

    Example:
        >>> import wn
        >>> from wn.similarity import path
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> spatula = ewn.synsets('spatula')[0]
        >>> path(spatula, ewn.synsets('pancake')[0])
        0.058823529411764705
        >>> path(spatula, ewn.synsets('utensil')[0])
        0.2
        >>> path(spatula, spatula)
        1.0
        >>> flip = ewn.synsets('flip', pos='v')[0]
        >>> turn_over = ewn.synsets('turn over', pos='v')[0]
        >>> path(flip, turn_over)
        0.0
        >>> path(flip, turn_over, simulate_root=True)
        0.16666666666666666

     """
    return 1 / (distance + 1)


def wup(synset1: Synset, synset2: Synset) -> float:
    """Return the Wu-Palmer similarity of *synset1* and *synset2*.

    Arguments:
        synset1: The first synset to compare.
        synset2: The second synset to compare.
        simulate_root: When :python:`True`, a fake root node connects
            all other roots; default: :python:`False`.

    Raises:
        wn.Error: When no path connects the *synset1* and *synset2*.

    Example:
        >>> import wn
        >>> from wn.similarity import wup
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> spatula = ewn.synsets('spatula')[0]
        >>> wup(spatula, ewn.synsets('pancake')[0])
        0.2
        >>> wup(spatula, ewn.synsets('utensil')[0])
        0.8
        >>> wup(spatula, spatula)
        1.0
        >>> flip = ewn.synsets('flip', pos='v')[0]
        >>> turn_over = ewn.synsets('turn over', pos='v')[0]
        >>> wup(flip, turn_over, simulate_root=True)
        0.2857142857142857

    """
    lch = synset1.lowest_common_hypernyms(synset2, simulate_root=True)[0]
    n3 = lch.max_depth() + 1
    n1 = len(synset1.shortest_path(lch, simulate_root=True))
    n2 = len(synset2.shortest_path(lch, simulate_root=True))
    return (2 * n3) / (n1 + n2 + 2 * n3)
def lch(
    synset1: Synset,
    synset2: Synset,
    max_depth: int,
    simulate_root: bool = False
) -> float:
    """Return the Leacock-Chodorow similarity between *synset1* and *synset2*.

    Arguments:
        synset1: The first synset to compare.
        synset2: The second synset to compare.
        max_depth: The taxonomy depth (see :func:`wn.taxonomy.taxonomy_depth`)
        simulate_root: When :python:`True`, a fake root node connects
            all other roots; default: :python:`False`.

    Example:
        >>> import wn, wn.taxonomy
        >>> from wn.similarity import lch
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> n_depth = wn.taxonomy.taxonomy_depth(ewn, 'n')
        >>> spatula = ewn.synsets('spatula')[0]
        >>> lch(spatula, ewn.synsets('pancake')[0], n_depth)
        0.8043728156701697
        >>> lch(spatula, ewn.synsets('utensil')[0], n_depth)
        2.0281482472922856
        >>> lch(spatula, spatula, n_depth)
        3.6375861597263857
        >>> v_depth = taxonomy.taxonomy_depth(ewn, 'v')
        >>> flip = ewn.synsets('flip', pos='v')[0]
        >>> turn_over = ewn.synsets('turn over', pos='v')[0]
        >>> lch(flip, turn_over, v_depth, simulate_root=True)
        1.3862943611198906

    """
    if max_depth <= 0:
        raise wn.Error('max_depth must be greater than 0')
    return -math.log((distance + 1) / (2 * max_depth))
