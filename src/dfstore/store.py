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
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Invalid name {name!r}. Names must match ^[a-zA-Z0-9_\\-]{{1,128}}$"
        )


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _detect_library(df: object) -> str:
    if isinstance(df, pd.DataFrame):
        return "pandas"
    if isinstance(df, pl.DataFrame):
        return "polars"
    raise TypeError(f"Expected pd.DataFrame or pl.DataFrame, got {type(df).__name__}")


class DFStore:
    def __init__(self, store_path: Path) -> None:
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

    def list(self, include_deleted: bool = False) -> builtins.list[DFRecord]:
        records = self._index.load()
        result = [
            r for r in records.values()
            if include_deleted or not r.deleted
        ]
        result.sort(key=lambda r: r.updated_at, reverse=True)
        return result

    # ── info ──────────────────────────────────────────────────────────────────

    def info(self, name: str) -> DFRecord:
        _validate_name(name)
        records = self._index.load()
        if name not in records:
            raise DFNotFoundError(f"'{name}' not found in the store.")
        return records[name]

    # ── search ────────────────────────────────────────────────────────────────

    def search(
        self,
        description: str | None = None,
        tags: builtins.list[str | dict[str, str]] | None = None,
        columns: builtins.list[str] | None = None,
    ) -> builtins.list[DFRecord]:
        if description is None and tags is None and columns is None:
            raise ValueError("At least one search criterion must be provided.")

        results = self.list()

        if description is not None:
            q = description.lower()
            results = [r for r in results if q in r.description.lower()]

        if tags is not None:
            results = [r for r in results if _tags_match(r.tags, tags)]

        if columns is not None:
            results = [r for r in results if _columns_match(r, columns)]

        return results

    # ── versions ──────────────────────────────────────────────────────────────

    def versions(self, name: str) -> builtins.list[VersionRecord]:
        _validate_name(name)
        records = self._index.load()
        if name not in records:
            raise DFNotFoundError(f"'{name}' not found in the store.")
        return builtins.list(sorted(records[name].versions, key=lambda v: v.version))

    # ── delete ────────────────────────────────────────────────────────────────

    def delete(self, name: str, hard: bool = False) -> None:
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

    # ── restore ───────────────────────────────────────────────────────────────

    def restore(self, name: str) -> None:
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
    current_version = record.versions[record.current_version - 1]
    current_cols = builtins.set(current_version.columns)
    return all(c in current_cols for c in columns)
