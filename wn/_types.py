
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Optional, Union
from pathlib import Path

# For functions taking a filesystem path as a str or a pathlib.Path
AnyPath = Union[str, Path]

# LMF versions for comparison
VersionInfo = tuple[int, ...]

# Synset and Sense relations map a relation type to one or more ids
RelationMap = Mapping[str, Sequence[str]]

# User-facing metadata representation
Metadata = dict[str, Any]

# A callable that returns a normalized word form for a given word form
NormalizeFunction = Callable[[str], str]

# Lemmatization returns a mapping of parts of speech (or None) to
# lists of wordforms that are potential lemmas for some query word
LemmatizeResult = dict[Optional[str], set[str]]

# A callable that returns a LemmatizationResult for a given word form
# and optional part of speech
LemmatizeFunction = Callable[[str, Optional[str]], LemmatizeResult]
