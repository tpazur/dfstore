"""dfstore — public API."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("dfstore")
except PackageNotFoundError:
    __version__ = "0.1.0"

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
    "preview",
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
    format: Literal["pd", "raw"] = "pd",
) -> builtins.list[DFRecord] | pd.DataFrame:
    """List all DataFrames in the store."""
    return DFStore(_resolve_path(store_path)).list(include_deleted=include_deleted, format=format)


def info(
    name: str,
    store_path: str | Path | None = None,
    format: Literal["pd", "raw"] = "pd",
) -> DFRecord | pd.DataFrame:
    """Return full metadata for a named DataFrame."""
    return DFStore(_resolve_path(store_path)).info(name, format=format)


def search(
    description: str | None = None,
    tags: builtins.list[str | dict[str, str]] | None = None,
    columns: builtins.list[str] | None = None,
    store_path: str | Path | None = None,
    format: Literal["pd", "raw"] = "pd",
) -> builtins.list[DFRecord] | pd.DataFrame:
    """Search DataFrames by description, tags, or columns."""
    return DFStore(_resolve_path(store_path)).search(
        description=description, tags=tags, columns=columns, format=format
    )


def versions(
    name: str,
    store_path: str | Path | None = None,
    format: Literal["pd", "raw"] = "pd",
) -> builtins.list[VersionRecord] | pd.DataFrame:
    """Return the version history for a named DataFrame."""
    return DFStore(_resolve_path(store_path)).versions(name, format=format)


def preview(
    name: str,
    n: int = 5,
    version: int | None = None,
    store_path: str | Path | None = None,
) -> dict:
    """Return the first *n* rows of a stored DataFrame as a plain dict."""
    return DFStore(_resolve_path(store_path)).preview(name, n=n, version=version)


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
