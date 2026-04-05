from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VersionRecord:
    """Metadata snapshot for a single saved version of a DataFrame.

    Created each time ``DFStore.save`` is called. Stores statistics about
    the DataFrame at save time as well as the diff relative to the previous
    version.
    """

    version: int
    """Monotonically increasing version number, starting at 1."""
    saved_at: datetime
    """UTC timestamp of when this version was saved."""
    notes: str
    """Optional free-text note describing what changed in this version."""
    shape: tuple[int, int]
    """(rows, columns) of the DataFrame at save time."""
    columns: list[str]
    """Ordered list of column names."""
    dtypes: dict[str, str]
    """Mapping of column name → dtype string."""
    null_counts: dict[str, int]
    """Mapping of column name → number of null/NaN values."""
    describe: dict[str, dict[str, float]]
    """Descriptive statistics (count, mean, std, …) for numeric columns."""
    shape_diff: tuple[int, int] | None
    """(row_delta, col_delta) relative to the previous version; ``None`` for v1."""
    columns_added: list[str]
    """Columns present in this version but not in the previous one."""
    columns_removed: list[str]
    """Columns present in the previous version but not in this one."""
    row_diff: int
    """Change in row count relative to the previous version."""
    library: str
    """The DataFrame library used when saving: ``'pandas'`` or ``'polars'``."""
    parquet_file: str
    """Path to the underlying Parquet file, relative to the store root."""


@dataclass
class DFRecord:
    """Top-level metadata entry for a stored DataFrame.

    One ``DFRecord`` exists per unique name in the store. It holds shared
    metadata (description, tags, timestamps) and the full list of
    ``VersionRecord`` objects for every save operation.
    """

    name: str
    """Unique identifier for this DataFrame in the store."""
    description: str
    """Human-readable description of the dataset."""
    tags: list[str | dict[str, str]]
    """List of plain-string tags or ``{"key": "value"}`` dict tags."""
    created_at: datetime
    """UTC timestamp of the first save."""
    updated_at: datetime
    """UTC timestamp of the most recent save."""
    current_version: int
    """Version number of the latest (non-deleted) save."""
    deleted: bool
    """``True`` if this record has been soft-deleted."""
    versions: list[VersionRecord] = field(default_factory=list)
    """All version records in chronological order."""
