"""DFStore: core business logic."""
from __future__ import annotations

import builtins
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pandas as pd
import polars as pl

from .diff import compute_diff
from .exceptions import DFNotFoundError, DFStoreError
from .metadata import MetadataIndex
from .models import DFRecord, VersionRecord
from .storage import compute_metadata, read_parquet, write_parquet

_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def _validate_name(name: str) -> None:
    """Raise ``ValueError`` if *name* does not match the allowed pattern."""
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid name {name!r}. Names must match ^[a-zA-Z0-9_\\-]{{1,128}}$"
        )


def _now() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(tz=timezone.utc)


def _detect_library(df: object) -> str:
    """Return ``'pandas'`` or ``'polars'`` based on the type of *df*."""
    if isinstance(df, pd.DataFrame):
        return "pandas"
    if isinstance(df, pl.DataFrame):
        return "polars"
    raise TypeError(f"Expected pd.DataFrame or pl.DataFrame, got {type(df).__name__}")


class DFStore:
    """Local DataFrame store backed by Parquet files and a JSON metadata index.

    All DataFrames are saved under *store_path* with the structure::

        store_path/
          index.json          ← metadata for all DataFrames
          data/
            <name>/
              v1.parquet
              v2.parquet
              …

    Every call to :meth:`save` creates a new versioned Parquet file and
    updates the metadata index atomically.
    """

    def __init__(self, store_path: Path) -> None:
        """Initialise the store at *store_path* (directory need not exist yet)."""
        self._store_path = store_path
        self._index = MetadataIndex(store_path)

    # ── save ──────────────────────────────────────────────────────────────────

    def save(
        self,
        df: pd.DataFrame | pl.DataFrame,
        name: str,
        description: str = "",
        tags: builtins.list[str | dict[str, str]] | None = None,
        notes: str = "",
        *,
        _now_fn=_now,
    ) -> VersionRecord:
        """Save *df* under *name* and return the new :class:`VersionRecord`.

        If *name* does not exist, a new record is created (version 1).
        If it already exists, a new version is appended with a diff against
        the previous version.

        Args:
            df: A pandas or polars DataFrame to store.
            name: Unique identifier (alphanumeric, ``_``, ``-``, max 128 chars).
            description: Human-readable description of the dataset.
            tags: List of plain strings or ``{"key": "value"}`` dicts.
            notes: Free-text note describing what changed in this version.

        Returns:
            The :class:`VersionRecord` created for this save.

        Raises:
            ValueError: If *name* contains invalid characters.
            DFStoreError: If *name* is currently soft-deleted.
        """
        _validate_name(name)
        library = _detect_library(df)
        meta = compute_metadata(df)
        records = self._index.load()

        if tags is None:
            tags = []

        now = _now_fn()

        if name not in records:
            # New record — version 1
            parquet_file = f"data/{name}/v1.parquet"
            vr = VersionRecord(
                version=1,
                saved_at=now,
                notes="Initial save",
                shape=meta["shape"],
                columns=meta["columns"],
                dtypes=meta["dtypes"],
                null_counts=meta["null_counts"],
                describe=meta["describe"],
                shape_diff=None,
                columns_added=[],
                columns_removed=[],
                row_diff=0,
                library=library,
                parquet_file=parquet_file,
            )
            record = DFRecord(
                name=name,
                description=description,
                tags=tags,
                created_at=now,
                updated_at=now,
                current_version=1,
                deleted=False,
                versions=[vr],
            )
            write_parquet(df, self._store_path / parquet_file)
            records[name] = record
            self._index.save(records)
            return vr

        record = records[name]
        if record.deleted:
            raise DFStoreError(
                f"'{name}' is soft-deleted. Restore it first or use a different name."
            )

        # Existing record — new version
        new_version = record.current_version + 1
        parquet_file = f"data/{name}/v{new_version}.parquet"

        prev_vr = record.versions[-1]
        diff = compute_diff(prev_vr, meta)

        vr = VersionRecord(
            version=new_version,
            saved_at=now,
            notes=notes,
            shape=meta["shape"],
            columns=meta["columns"],
            dtypes=meta["dtypes"],
            null_counts=meta["null_counts"],
            describe=meta["describe"],
            shape_diff=diff["shape_diff"],
            columns_added=diff["columns_added"],
            columns_removed=diff["columns_removed"],
            row_diff=diff["row_diff"],
            library=library,
            parquet_file=parquet_file,
        )

        record.versions.append(vr)
        record.current_version = new_version
        record.updated_at = now
        if description:
            record.description = description
        record.tags = tags if tags else record.tags

        write_parquet(df, self._store_path / parquet_file)
        self._index.save(records)
        return vr

    # ── get ───────────────────────────────────────────────────────────────────

    def get(
        self,
        name: str,
        version: int | None = None,
        as_library: Literal["pandas", "polars"] | None = None,
    ) -> pd.DataFrame | pl.DataFrame:
        """Retrieve a stored DataFrame by name and optional version.

        Args:
            name: The DataFrame name.
            version: Version number to retrieve; defaults to the latest version.
            as_library: Return as ``'pandas'`` or ``'polars'``; defaults to the
                library used when the version was saved.

        Raises:
            DFNotFoundError: If *name* does not exist or is soft-deleted.
            ValueError: If *version* is out of range.
        """
        _validate_name(name)
        records = self._index.load()

        if name not in records or records[name].deleted:
            raise DFNotFoundError(f"'{name}' not found in the store.")

        record = records[name]
        if version is None:
            version = record.current_version

        if version < 1 or version > record.current_version:
            raise ValueError(
                f"Version {version} out of range for '{name}' "
                f"(1–{record.current_version})."
            )

        vr = record.versions[version - 1]
        library = as_library or vr.library
        return read_parquet(self._store_path / vr.parquet_file, library)

    # ── list ──────────────────────────────────────────────────────────────────

    def list(
        self,
        include_deleted: bool = False,
        format: Literal["pd", "raw"] = "pd",
    ) -> builtins.list[DFRecord] | pd.DataFrame:
        """Return all stored DataFrames, sorted by most-recently-updated first.

        Args:
            include_deleted: If ``True``, soft-deleted records are included.
            format: ``'raw'`` returns a list of :class:`DFRecord`; ``'pd'``
                returns a pandas DataFrame summary.
        """
        records = self._index.load()
        result = [
            r for r in records.values()
            if include_deleted or not r.deleted
        ]
        result.sort(key=lambda r: r.updated_at, reverse=True)
        if format == "raw":
            return result
        return _records_to_df(result)

    # ── info ──────────────────────────────────────────────────────────────────

    def info(
        self,
        name: str,
        format: Literal["pd", "raw"] = "pd",
    ) -> DFRecord | pd.DataFrame:
        """Return the full metadata record for *name*.

        Args:
            name: The DataFrame name.
            format: ``'raw'`` returns a :class:`DFRecord`; ``'pd'`` returns a
                single-row pandas DataFrame.

        Raises:
            DFNotFoundError: If *name* does not exist in the store.
        """
        _validate_name(name)
        records = self._index.load()
        if name not in records:
            raise DFNotFoundError(f"'{name}' not found in the store.")
        record = records[name]
        if format == "raw":
            return record
        return _records_to_df([record])

    # ── search ────────────────────────────────────────────────────────────────

    def search(
        self,
        description: str | None = None,
        tags: builtins.list[str | dict[str, str]] | None = None,
        columns: builtins.list[str] | None = None,
        format: Literal["pd", "raw"] = "pd",
    ) -> builtins.list[DFRecord] | pd.DataFrame:
        """Search active DataFrames by description substring, tags, or column names.

        All provided criteria are ANDed together. At least one must be given.

        Args:
            description: Case-insensitive substring to match against each record's
                description.
            tags: Tags that must all be present on a record.
            columns: Column names that must all be present in the current version.
            format: ``'raw'`` returns a list of :class:`DFRecord`; ``'pd'`` returns
                a pandas DataFrame.

        Raises:
            ValueError: If no search criteria are provided.
        """
        if description is None and tags is None and columns is None:
            raise ValueError("At least one search criterion must be provided.")

        results = self.list(format="raw")

        if description is not None:
            q = description.lower()
            results = [r for r in results if q in r.description.lower()]

        if tags is not None:
            results = [r for r in results if _tags_match(r.tags, tags)]

        if columns is not None:
            results = [r for r in results if _columns_match(r, columns)]

        if format == "raw":
            return results
        return _records_to_df(results)

    # ── versions ──────────────────────────────────────────────────────────────

    def versions(
        self,
        name: str,
        format: Literal["pd", "raw"] = "pd",
    ) -> builtins.list[VersionRecord] | pd.DataFrame:
        """Return all version records for *name* in chronological order.

        Args:
            name: The DataFrame name.
            format: ``'raw'`` returns a list of :class:`VersionRecord`; ``'pd'``
                returns a pandas DataFrame.

        Raises:
            DFNotFoundError: If *name* does not exist in the store.
        """
        _validate_name(name)
        records = self._index.load()
        if name not in records:
            raise DFNotFoundError(f"'{name}' not found in the store.")
        vrs = builtins.list(sorted(records[name].versions, key=lambda v: v.version))
        if format == "raw":
            return vrs
        return _versions_to_df(vrs)

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, name: str, hard: bool = False) -> None:
        """Delete a stored DataFrame.

        Args:
            name: The DataFrame name.
            hard: If ``False`` (default), marks the record as deleted but keeps
                all data on disk. If ``True``, removes the metadata entry and
                deletes the entire ``data/<name>/`` directory permanently.

        Raises:
            DFNotFoundError: If *name* does not exist.
            DFStoreError: If attempting a soft-delete on an already-deleted record.
        """
        _validate_name(name)
        records = self._index.load()
        if name not in records:
            raise DFNotFoundError(f"'{name}' not found in the store.")

        if hard:
            del records[name]
            self._index.save(records)
            data_dir = self._store_path / "data" / name
            if data_dir.exists():
                import shutil
                shutil.rmtree(data_dir)
        else:
            if records[name].deleted:
                raise DFStoreError(f"'{name}' is already deleted.")
            records[name].deleted = True
            self._index.save(records)

    # ── preview ───────────────────────────────────────────────────────────────

    def preview(self, name: str, n: int = 5, version: int | None = None) -> dict:
        """Return the first *n* rows of a stored DataFrame without loading it fully.

        Uses ``pyarrow.parquet.ParquetFile.iter_batches`` so only the first
        row-group batch is decoded — the rest of the file is never touched.
        """
        import pyarrow.parquet as pq

        _validate_name(name)
        records = self._index.load()
        if name not in records or records[name].deleted:
            raise DFNotFoundError(f"'{name}' not found in the store.")

        record = records[name]
        if version is None:
            version = record.current_version
        if version < 1 or version > record.current_version:
            raise ValueError(
                f"Version {version} out of range for '{name}' (1–{record.current_version})."
            )

        path = self._store_path / record.versions[version - 1].parquet_file
        pf = pq.ParquetFile(path)
        batch = next(pf.iter_batches(batch_size=n))
        columns = batch.schema.names
        rows_dict = batch.to_pydict()

        def _safe(v):
            if v is None:
                return None
            if isinstance(v, float) and (v != v):  # NaN
                return None
            try:
                return v if isinstance(v, (bool, int, float, str)) else str(v)
            except Exception:
                return str(v)

        rows = [
            [_safe(rows_dict[col][i]) for col in columns]
            for i in range(min(n, len(rows_dict[columns[0]])))
        ]
        return {"columns": columns, "rows": rows}

    # ── restore ───────────────────────────────────────────────────────────────

    def restore(self, name: str) -> None:
        """Restore a soft-deleted DataFrame, making it active again.

        Raises:
            DFNotFoundError: If *name* does not exist in the store.
            DFStoreError: If *name* is not currently soft-deleted.
        """
        _validate_name(name)
        records = self._index.load()
        if name not in records:
            raise DFNotFoundError(f"'{name}' not found in the store.")
        if not records[name].deleted:
            raise DFStoreError(f"'{name}' is not deleted.")
        records[name].deleted = False
        self._index.save(records)


# ── helpers ───────────────────────────────────────────────────────────────────

def _tags_match(
    record_tags: builtins.list[str | dict[str, str]],
    query_tags: builtins.list[str | dict[str, str]],
) -> bool:
    """Return ``True`` if all *query_tags* are present in *record_tags*."""
    for qt in query_tags:
        if isinstance(qt, str):
            if qt not in record_tags:
                return False
        elif isinstance(qt, dict):
            found = any(
                isinstance(rt, dict) and rt == qt
                for rt in record_tags
            )
            if not found:
                return False
    return True


def _columns_match(record: DFRecord, columns: builtins.list[str]) -> bool:
    """Return ``True`` if all *columns* are present in the current version of *record*."""
    current_version = record.versions[record.current_version - 1]
    current_cols = builtins.set(current_version.columns)
    return all(c in current_cols for c in columns)


def _records_to_df(records: builtins.list[DFRecord]) -> pd.DataFrame:
    """Convert a list of :class:`DFRecord` objects to a summary pandas DataFrame."""
    rows = [
        {
            "name": r.name,
            "description": r.description,
            "tags": r.tags,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "current_version": r.current_version,
            "deleted": r.deleted,
        }
        for r in records
    ]
    return pd.DataFrame(rows, columns=["name", "description", "tags", "created_at", "updated_at", "current_version", "deleted"])


def _versions_to_df(versions: builtins.list[VersionRecord]) -> pd.DataFrame:
    """Convert a list of :class:`VersionRecord` objects to a pandas DataFrame."""
    rows = [
        {
            "version": v.version,
            "saved_at": v.saved_at,
            "notes": v.notes,
            "shape": v.shape,
            "columns": v.columns,
            "library": v.library,
            "shape_diff": v.shape_diff,
            "columns_added": v.columns_added,
            "columns_removed": v.columns_removed,
            "row_diff": v.row_diff,
        }
        for v in versions
    ]
    return pd.DataFrame(rows, columns=["version", "saved_at", "notes", "shape", "columns", "library", "shape_diff", "columns_added", "columns_removed", "row_diff"])
