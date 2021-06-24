
"""Synset similarity metrics."""

from typing import List
import math

import wn
from wn.constants import ADJ, ADJ_SAT
from wn._core import Synset
from wn.ic import Freq, information_content


def path(synset1: Synset, synset2: Synset, simulate_root: bool = False) -> float:
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
    _check_if_pos_compatible(synset1.pos, synset2.pos)
    try:
        path = synset1.shortest_path(synset2, simulate_root=simulate_root)
    except wn.Error:
        distance = float('inf')
    else:
        distance = len(path)
    return 1 / (distance + 1)


def wup(synset1: Synset, synset2: Synset, simulate_root=False) -> float:
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
    _check_if_pos_compatible(synset1.pos, synset2.pos)
    lcs_list = _least_common_subsumers(synset1, synset2, simulate_root)
    lcs = lcs_list[0]
    i = len(synset1.shortest_path(lcs, simulate_root=simulate_root))
    j = len(synset2.shortest_path(lcs, simulate_root=simulate_root))
    k = lcs.max_depth() + 1
    return (2*k) / (i + j + 2*k)


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
    _check_if_pos_compatible(synset1.pos, synset2.pos)
    distance = len(synset1.shortest_path(synset2, simulate_root=simulate_root))
    if max_depth <= 0:
        raise wn.Error('max_depth must be greater than 0')
    return -math.log((distance + 1) / (2 * max_depth))


def res(synset1: Synset, synset2: Synset, ic: Freq) -> float:
    """Return the Resnik similarity between *synset1* and *synset2*.

    Arguments:
        synset1: The first synset to compare.
        synset2: The second synset to compare.
        ic: Information Content weights.

    Example:
        >>> import wn, wn.ic, wn.taxonomy
        >>> from wn.similarity import res
        >>> pwn = wn.Wordnet('pwn:3.0')
        >>> ic = wn.ic.load('~/nltk_data/corpora/wordnet_ic/ic-brown.dat', pwn)
        >>> spatula = pwn.synsets('spatula')[0]
        >>> res(spatula, pwn.synsets('pancake')[0], ic)
        0.8017591149538994
        >>> res(spatula, pwn.synsets('utensil')[0], ic)
        5.87738923441087

    """
    _check_if_pos_compatible(synset1.pos, synset2.pos)
    lcs = _most_informative_lcs(synset1, synset2, ic)
    return information_content(lcs, ic)


def jcn(synset1: Synset, synset2: Synset, ic: Freq) -> float:
    """Return the Jiang-Conrath similarity of two synsets.

    Arguments:
        synset1: The first synset to compare.
        synset2: The second synset to compare.
        ic: Information Content weights.

    Example:
        >>> import wn, wn.ic, wn.taxonomy
        >>> from wn.similarity import jcn
        >>> pwn = wn.Wordnet('pwn:3.0')
        >>> ic = wn.ic.load('~/nltk_data/corpora/wordnet_ic/ic-brown.dat', pwn)
        >>> spatula = pwn.synsets('spatula')[0]
        >>> jcn(spatula, pwn.synsets('pancake')[0], ic)
        0.04061799236354239
        >>> jcn(spatula, pwn.synsets('utensil')[0], ic)
        0.10794048564613007

    """
    _check_if_pos_compatible(synset1.pos, synset2.pos)
    ic1 = information_content(synset1, ic)
    ic2 = information_content(synset2, ic)
    lcs = _most_informative_lcs(synset1, synset2, ic)
    ic_lcs = information_content(lcs, ic)
    if ic1 == ic2 == ic_lcs == 0:
        return 0
    elif ic1 + ic2 == 2 * ic_lcs:
        return float('inf')
    else:
        return 1 / (ic1 + ic2 - 2 * ic_lcs)


def lin(synset1: Synset, synset2: Synset, ic: Freq) -> float:
    """Return the Lin similarity of two synsets.

    Arguments:
        synset1: The first synset to compare.
        synset2: The second synset to compare.
        ic: Information Content weights.

    Example:
        >>> import wn, wn.ic, wn.taxonomy
        >>> from wn.similarity import lin
        >>> pwn = wn.Wordnet('pwn:3.0')
        >>> ic = wn.ic.load('~/nltk_data/corpora/wordnet_ic/ic-brown.dat', pwn)
        >>> spatula = pwn.synsets('spatula')[0]
        >>> lin(spatula, pwn.synsets('pancake')[0], ic)
        0.061148956278604116
        >>> lin(spatula, pwn.synsets('utensil')[0], ic)
        0.5592415686750427

    """
    _check_if_pos_compatible(synset1.pos, synset2.pos)
    lcs = _most_informative_lcs(synset1, synset2, ic)
    ic1 = information_content(synset1, ic)
    ic2 = information_content(synset2, ic)
    if ic1 == 0 or ic2 == 0:
        return 0.0
    return 2 * information_content(lcs, ic) / (ic1 + ic2)


# Helper functions

def _least_common_subsumers(
    synset1: Synset,
    synset2: Synset,
    simulate_root: bool
) -> List[Synset]:
    lcs = synset1.lowest_common_hypernyms(synset2, simulate_root=simulate_root)
    if not lcs:
        raise wn.Error(f'no common hypernyms for {synset1!r} and {synset2!r}')
    return lcs


def _most_informative_lcs(synset1: Synset, synset2: Synset, ic: Freq) -> Synset:
    pos_ic = ic[synset1.pos]
    lcs = _least_common_subsumers(synset1, synset2, False)
    return max(lcs, key=lambda ss: pos_ic[ss.id])


def _check_if_pos_compatible(pos1: str, pos2: str) -> None:
    _pos1 = ADJ if pos1 == ADJ_SAT else pos1
    _pos2 = ADJ if pos2 == ADJ_SAT else pos2
    if _pos1 != _pos2:
        raise wn.Error('synsets must have the same part of speech')
