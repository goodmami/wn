from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeAlias

# For the below, use type statement instead of TypeAlias from Python 3.12

# For functions taking a filesystem path as a str or a pathlib.Path
AnyPath: TypeAlias = str | Path

# LMF versions for comparison
VersionInfo: TypeAlias = tuple[int, ...]

# Synset and Sense relations map a relation type to one or more ids
RelationMap: TypeAlias = Mapping[str, Sequence[str]]

# User-facing metadata representation
Metadata: TypeAlias = dict[str, Any]

# A callable that returns a normalized word form for a given word form
NormalizeFunction: TypeAlias = Callable[[str], str]

# Lemmatization returns a mapping of parts of speech (or None) to
# lists of wordforms that are potential lemmas for some query word
LemmatizeResult: TypeAlias = dict[str | None, set[str]]

# A callable that returns a LemmatizationResult for a given word form
# and optional part of speech
LemmatizeFunction: TypeAlias = Callable[[str, str | None], LemmatizeResult]
