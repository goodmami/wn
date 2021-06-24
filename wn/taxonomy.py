
"""Functions for working with hypernym/hyponym taxonomies."""

from typing import Optional, Tuple, List, Set, Dict, TYPE_CHECKING

import wn
from wn.constants import ADJ, ADJ_SAT
from wn._util import flatten
from wn import _core

if TYPE_CHECKING:
    from wn._core import Wordnet, Synset


_FAKE_ROOT = '*ROOT*'


def roots(wordnet: 'Wordnet', pos: Optional[str] = None) -> List['Synset']:
    """Return the list of root synsets in *wordnet*.

    Arguments:

        wordnet: The wordnet from which root synsets are found.

        pos: If given, only return synsets with the specified part of
            speech.

    Example:

        >>> import wn, wn.taxonomy
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> len(wn.taxonomy.roots(ewn, pos='v'))
        573


    """
    return [ss for ss in _synsets_for_pos(wordnet, pos) if not ss.hypernyms()]


def leaves(wordnet: 'Wordnet', pos: Optional[str] = None) -> List['Synset']:
    """Return the list of leaf synsets in *wordnet*.

    Arguments:

        wordnet: The wordnet from which leaf synsets are found.

        pos: If given, only return synsets with the specified part of
            speech.

    Example:

        >>> import wn, wn.taxonomy
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> len(wn.taxonomy.leaves(ewn, pos='v'))
        10525

    """
    return [ss for ss in _synsets_for_pos(wordnet, pos) if not ss.hyponyms()]


def taxonomy_depth(wordnet: 'Wordnet', pos: str) -> int:
    """Return the list of leaf synsets in *wordnet*.

    Arguments:

        wordnet: The wordnet for which the taxonomy depth will be
            calculated.

        pos: The part of speech for which the taxonomy depth will be
            calculated.

    Example:

        >>> import wn, wn.taxonomy
        >>> ewn = wn.Wordnet('ewn:2020')
        >>> wn.taxonomy.taxonomy_depth(ewn, 'n')
        19

    """
    seen: Set['Synset'] = set()
    depth = 0
    for ss in _synsets_for_pos(wordnet, pos):
        if all(hyp in seen for hyp in ss.hypernyms()):
            continue
        paths = ss.hypernym_paths()
        if paths:
            depth = max(depth, max(len(path) for path in paths))
            seen.update(hyp for path in paths for hyp in path)
    return depth


def _synsets_for_pos(wordnet: 'Wordnet', pos: Optional[str]) -> List['Synset']:
    """Get the list of synsets for a part of speech. If *pos* is 'a' or
    's', also include those for the other.

    """
    synsets = wordnet.synsets(pos=pos)
    if pos == ADJ:
        synsets.extend(wordnet.synsets(pos=ADJ_SAT))
    elif pos == ADJ_SAT:
        synsets.extend(wordnet.synsets(pos=ADJ))
    return synsets


def _hypernym_paths(
        synset: 'Synset', simulate_root: bool, include_self: bool
) -> List[List['Synset']]:
    paths = list(synset.relation_paths('hypernym', 'instance_hypernym'))
    if include_self:
        paths = [[synset] + path for path in paths] or [[synset]]
    if simulate_root and synset.id != _FAKE_ROOT:
        root = _core.Synset.empty(
            id=_FAKE_ROOT, _lexid=synset._lexid, _wordnet=synset._wordnet
        )
        paths = [path + [root] for path in paths] or [[root]]
    return paths


def hypernym_paths(
    synset: 'Synset',
    simulate_root: bool = False
) -> List[List['Synset']]:
    """Return the list of hypernym paths to a root synset.

    Arguments:

        synset: The starting synset for paths to a root.

        simulate_root: If :python:`True`, find the path to a simulated
            root node.

    Example:

        >>> import wn, wn.taxonomy
        >>> dog = wn.synsets('dog', pos='n')[0]
        >>> for path in wn.taxonomy.hypernym_paths(dog):
        ...     for i, ss in enumerate(path):
        ...         print(' ' * i, ss, ss.lemmas()[0])
        ...
         Synset('pwn-02083346-n') canine
          Synset('pwn-02075296-n') carnivore
           Synset('pwn-01886756-n') eutherian mammal
            Synset('pwn-01861778-n') mammalian
             Synset('pwn-01471682-n') craniate
              Synset('pwn-01466257-n') chordate
               Synset('pwn-00015388-n') animal
                Synset('pwn-00004475-n') organism
                 Synset('pwn-00004258-n') animate thing
                  Synset('pwn-00003553-n') unit
                   Synset('pwn-00002684-n') object
                    Synset('pwn-00001930-n') physical entity
                     Synset('pwn-00001740-n') entity
         Synset('pwn-01317541-n') domesticated animal
          Synset('pwn-00015388-n') animal
           Synset('pwn-00004475-n') organism
            Synset('pwn-00004258-n') animate thing
             Synset('pwn-00003553-n') unit
              Synset('pwn-00002684-n') object
               Synset('pwn-00001930-n') physical entity
                Synset('pwn-00001740-n') entity

    """
    return _hypernym_paths(synset, simulate_root, False)


def min_depth(synset: 'Synset', simulate_root: bool = False) -> int:
    """Return the minimum taxonomy depth of the synset.

    Arguments:

        synset: The starting synset for paths to a root.

        simulate_root: If :python:`True`, find the depth to a
            simulated root node.

    Example:

        >>> import wn, wn.taxonomy
        >>> dog = wn.synsets('dog', pos='n')[0]
        >>> wn.taxonomy.min_depth(dog)
        8

    """
    return min(
        (len(path) for path in synset.hypernym_paths(simulate_root=simulate_root)),
        default=0
    )


def max_depth(synset: 'Synset', simulate_root: bool = False) -> int:
    """Return the maximum taxonomy depth of the synset.

    Arguments:

        synset: The starting synset for paths to a root.

        simulate_root: If :python:`True`, find the depth to a
            simulated root node.

    Example:

        >>> import wn, wn.taxonomy
        >>> dog = wn.synsets('dog', pos='n')[0]
        >>> wn.taxonomy.max_depth(dog)
        13

    """
    return max(
        (len(path) for path in synset.hypernym_paths(simulate_root=simulate_root)),
        default=0
    )


def _shortest_hyp_paths(
        synset: 'Synset', other: 'Synset', simulate_root: bool
) -> Dict[Tuple['Synset', int], List['Synset']]:
    if synset == other:
        return {(synset, 0): []}

    from_self = _hypernym_paths(synset, simulate_root, True)
    from_other = _hypernym_paths(other, simulate_root, True)
    common = set(flatten(from_self)).intersection(flatten(from_other))

    if not common:
        return {}

    # Compute depths of common hypernyms from their distances.
    # Doing this now avoid more expensive lookups later.
    depths: Dict['Synset', int] = {}
    # subpaths accumulates paths to common hypernyms from both sides
    subpaths: Dict['Synset', Tuple[List[List['Synset']], List[List['Synset']]]]
    subpaths = {ss: ([], []) for ss in common}
    for which, paths in (0, from_self), (1, from_other):
        for path in paths:
            for dist, ss in enumerate(path):
                if ss in common:
                    # synset or other subpath to ss (not including ss)
                    subpaths[ss][which].append(path[:dist + 1])
                    # keep maximum depth
                    depth = len(path) - dist - 1
                    if ss not in depths or depths[ss] < depth:
                        depths[ss] = depth

    shortest: Dict[Tuple['Synset', int], List['Synset']] = {}
    for ss in common:
        from_self_subpaths, from_other_subpaths = subpaths[ss]
        shortest_from_self = min(from_self_subpaths, key=len)
        # for the other path, we need to reverse it and remove the pivot synset
        shortest_from_other = min(from_other_subpaths, key=len)[-2::-1]
        shortest[(ss, depths[ss])] = shortest_from_self + shortest_from_other

    return shortest


def shortest_path(
        synset: 'Synset', other: 'Synset', simulate_root: bool = False
) -> List['Synset']:
    """Return the shortest path from *synset* to the *other* synset.

    Arguments:
        other: endpoint synset of the path
        simulate_root: if :python:`True`, ensure any two synsets
          are always connected by positing a fake root node

    Example:

        >>> import wn, wn.taxonomy
        >>> dog = ewn.synsets('dog', pos='n')[0]
        >>> squirrel = ewn.synsets('squirrel', pos='n')[0]
        >>> for ss in wn.taxonomy.shortest_path(dog, squirrel):
        ...     print(ss.lemmas())
        ...
        ['canine', 'canid']
        ['carnivore']
        ['eutherian mammal', 'placental', 'placental mammal', 'eutherian']
        ['rodent', 'gnawer']
        ['squirrel']

    """
    pathmap = _shortest_hyp_paths(synset, other, simulate_root)
    key = min(pathmap, key=lambda key: len(pathmap[key]), default=None)
    if key is None:
        raise wn.Error(f'no path between {synset!r} and {other!r}')
    return pathmap[key][1:]


def common_hypernyms(
        synset: 'Synset', other: 'Synset', simulate_root: bool = False
) -> List['Synset']:
    """Return the common hypernyms for the current and *other* synsets.

    Arguments:
        other: synset that is a hyponym of any shared hypernyms
        simulate_root: if :python:`True`, ensure any two synsets
          always share a hypernym by positing a fake root node

    Example:

        >>> import wn, wn.taxonomy
        >>> dog = ewn.synsets('dog', pos='n')[0]
        >>> squirrel = ewn.synsets('squirrel', pos='n')[0]
        >>> for ss in wn.taxonomy.common_hypernyms(dog, squirrel):
        ...     print(ss.lemmas())
        ...
        ['entity']
        ['physical entity']
        ['object', 'physical object']
        ['unit', 'whole']
        ['animate thing', 'living thing']
        ['organism', 'being']
        ['fauna', 'beast', 'animate being', 'brute', 'creature', 'animal']
        ['chordate']
        ['craniate', 'vertebrate']
        ['mammalian', 'mammal']
        ['eutherian mammal', 'placental', 'placental mammal', 'eutherian']

    """
    from_self = _hypernym_paths(synset, simulate_root, True)
    from_other = _hypernym_paths(other, simulate_root, True)
    common = set(flatten(from_self)).intersection(flatten(from_other))
    return sorted(common)


def lowest_common_hypernyms(
        synset: 'Synset', other: 'Synset', simulate_root: bool = False
) -> List['Synset']:
    """Return the common hypernyms furthest from the root.

    Arguments:
        other: synset that is a hyponym of any shared hypernyms
        simulate_root: if :python:`True`, ensure any two synsets
          always share a hypernym by positing a fake root node

    Example:

        >>> import wn, wn.taxonomy
        >>> dog = ewn.synsets('dog', pos='n')[0]
        >>> squirrel = ewn.synsets('squirrel', pos='n')[0]
        >>> len(wn.taxonomy.lowest_common_hypernyms(dog, squirrel))
        1
        >>> wn.taxonomy.lowest_common_hypernyms(dog, squirrel)[0].lemmas()
        ['eutherian mammal', 'placental', 'placental mammal', 'eutherian']

    """
    pathmap = _shortest_hyp_paths(synset, other, simulate_root)
    # keys of pathmap are (synset, depth_of_synset)
    max_depth: int = max([depth for _, depth in pathmap], default=-1)
    if max_depth == -1:
        return []
    else:
        return [ss for ss, d in pathmap if d == max_depth]
