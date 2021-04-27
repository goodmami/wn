
from typing import Union, Callable, Mapping, Sequence, Dict, Any, Iterator
from pathlib import Path

# For functions taking a filesystem path as a str or a pathlib.Path
AnyPath = Union[str, Path]

# Synset and Sense relations map a relation type to one or more ids
RelationMap = Mapping[str, Sequence[str]]

# User-facing metadata representation
Metadata = Dict[str, Any]

# A function that returns a normalized word form for a given word form
NormalizeFunction = Callable[[str], str]

# A callable class or function that yields lemmatized words for a
# given word form and part of speech
LemmatizerInstance = Callable[[str, str], Iterator[str]]
