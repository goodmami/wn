
from typing import Union, Mapping, Sequence, Dict, Any
from pathlib import Path

# For functions taking a filesystem path as a str or a pathlib.Path
AnyPath = Union[str, Path]

# Synset and Sense relations map a relation type to one or more ids
RelationMap = Mapping[str, Sequence[str]]

# User-facing metadata representation
Metadata = Dict[str, Any]
