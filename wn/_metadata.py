from typing import Protocol, TypedDict


class Metadata(TypedDict, total=False):
    # For these, see https://globalwordnet.github.io/schemas/dc/
    contributor: str
    coverage: str
    creator: str
    date: str
    description: str
    format: str
    identifier: str
    publisher: str
    relation: str
    rights: str
    source: str
    subject: str
    title: str
    type: str
    # Additional WN-LMF metadata
    status: str
    note: str
    confidenceScore: float


class HasMetadata(Protocol):
    @property
    def _metadata(self) -> Metadata | None:
        return None

    def metadata(self) -> Metadata:
        """Return the associated metadata."""
        return self._metadata if self._metadata is not None else Metadata()

    def confidence(self) -> float:
        """Return the confidence score.

        If the confidenceScore metadata is available, return it. If not,
        use a default confidence value.
        """
        ...
