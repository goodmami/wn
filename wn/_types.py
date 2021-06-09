
from typing import (
    Optional, Union, Callable, Mapping, Sequence, Dict, Set, Any,
)
from pathlib import Path

# For functions taking a filesystem path as a str or a pathlib.Path
AnyPath = Union[str, Path]

# Synset and Sense relations map a relation type to one or more ids
RelationMap = Mapping[str, Sequence[str]]

# User-facing metadata representation
Metadata = Dict[str, Any]

# A callable that returns a normalized word form for a given word form
NormalizeFunction = Callable[[str], str]

# Lemmatization returns a mapping of parts of speech (or None) to
# lists of wordforms that are potential lemmas for some query word
LemmatizeResult = Dict[Optional[str], Set[str]]

# A callable that returns a LemmatizationResult for a given word form
# and optional part of speech
LemmatizeFunction = Callable[[str, Optional[str]], LemmatizeResult]
