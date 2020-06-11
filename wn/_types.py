
from typing import Union, Mapping, Sequence
from pathlib import Path

# For functions taking a filesystem path as a str or a pathlib.Path
AnyPath = Union[str, Path]

# Synset and Sense relations map a relation type to one or more ids
RelationMap = Mapping[str, Sequence[str]]
