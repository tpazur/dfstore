"""dfstore — public API."""
from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import Literal

import pandas as pd
import polars as pl

from .exceptions import DFNameConflictError, DFNotFoundError, DFStoreError
from .models import DFRecord, VersionRecord
from .store import DFStore

__all__ = [
    "save",
    "get",
    "list",
    "info",
    "search",
    "versions",
    "delete",
    "restore",
    "DFStore",
    "DFRecord",
    "VersionRecord",
    "DFStoreError",
    "DFNotFoundError",
    "DFNameConflictError",
]


def _resolve_path(store_path: str | Path | None) -> Path:
    if store_path is not None:
        return Path(store_path)
    env = os.environ.get("DFSTORE_PATH")
    if env:
        return Path(env)
    return Path.home() / ".dfstore"


def save(
    df: pd.DataFrame | pl.DataFrame,
    name: str,
    description: str = "",
    tags: builtins.list[str | dict[str, str]] | None = None,
    notes: str = "",
    store_path: str | Path | None = None,
) -> VersionRecord:
    """Save a DataFrame to the store."""
    return DFStore(_resolve_path(store_path)).save(
        df, name, description=description, tags=tags, notes=notes
    )


def get(
    name: str,
    version: int | None = None,
    as_library: Literal["pandas", "polars"] | None = None,
    store_path: str | Path | None = None,
) -> pd.DataFrame | pl.DataFrame:
    """Retrieve a DataFrame from the store."""
    return DFStore(_resolve_path(store_path)).get(name, version=version, as_library=as_library)


def list(  # noqa: A001
    include_deleted: bool = False,
    store_path: str | Path | None = None,
) -> builtins.list[DFRecord]:
    """List all DataFrames in the store."""
    return DFStore(_resolve_path(store_path)).list(include_deleted=include_deleted)


def info(
    name: str,
    store_path: str | Path | None = None,
) -> DFRecord:
    """Return full metadata for a named DataFrame."""
    return DFStore(_resolve_path(store_path)).info(name)


def search(
    description: str | None = None,
    tags: builtins.list[str | dict[str, str]] | None = None,
    columns: builtins.list[str] | None = None,
    store_path: str | Path | None = None,
) -> builtins.list[DFRecord]:
    """Search DataFrames by description, tags, or columns."""
    return DFStore(_resolve_path(store_path)).search(
        description=description, tags=tags, columns=columns
    )


def versions(
    name: str,
    store_path: str | Path | None = None,
) -> builtins.list[VersionRecord]:
    """Return the version history for a named DataFrame."""
    return DFStore(_resolve_path(store_path)).versions(name)


def delete(
    name: str,
    hard: bool = False,
    store_path: str | Path | None = None,
) -> None:
    """Delete a DataFrame (soft by default, hard if hard=True)."""
    DFStore(_resolve_path(store_path)).delete(name, hard=hard)


def restore(
    name: str,
    store_path: str | Path | None = None,
) -> None:
    """Restore a soft-deleted DataFrame."""
    DFStore(_resolve_path(store_path)).restore(name)
