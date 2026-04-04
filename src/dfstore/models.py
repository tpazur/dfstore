from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VersionRecord:
    version: int
    saved_at: datetime
    notes: str
    shape: tuple[int, int]
    columns: list[str]
    dtypes: dict[str, str]
    null_counts: dict[str, int]
    describe: dict[str, dict[str, float]]
    shape_diff: tuple[int, int] | None  # None for v1
    columns_added: list[str]
    columns_removed: list[str]
    row_diff: int
    library: str  # 'pandas' or 'polars'
    parquet_file: str  # relative path from store root


@dataclass
class DFRecord:
    name: str
    description: str
    tags: list[str | dict[str, str]]
    created_at: datetime
    updated_at: datetime
    current_version: int
    deleted: bool
    versions: list[VersionRecord] = field(default_factory=list)
