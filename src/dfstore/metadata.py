"""Read/write index.json atomically."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import DFRecord, VersionRecord


def _parse_dt(s: str) -> datetime:
    # Support both with and without microseconds
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s!r}")


def _fmt_dt(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _version_to_dict(v: VersionRecord) -> dict:
    return {
        "version": v.version,
        "saved_at": _fmt_dt(v.saved_at),
        "notes": v.notes,
        "shape": list(v.shape),
        "columns": v.columns,
        "dtypes": v.dtypes,
        "null_counts": v.null_counts,
        "describe": v.describe,
        "shape_diff": list(v.shape_diff) if v.shape_diff is not None else None,
        "columns_added": v.columns_added,
        "columns_removed": v.columns_removed,
        "row_diff": v.row_diff,
        "library": v.library,
        "parquet_file": v.parquet_file,
    }


def _version_from_dict(d: dict) -> VersionRecord:
    return VersionRecord(
        version=d["version"],
        saved_at=_parse_dt(d["saved_at"]),
        notes=d["notes"],
        shape=tuple(d["shape"]),
        columns=d["columns"],
        dtypes=d["dtypes"],
        null_counts=d["null_counts"],
        describe=d.get("describe", {}),
        shape_diff=tuple(d["shape_diff"]) if d.get("shape_diff") is not None else None,
        columns_added=d.get("columns_added", []),
        columns_removed=d.get("columns_removed", []),
        row_diff=d.get("row_diff", 0),
        library=d["library"],
        parquet_file=d["parquet_file"],
    )


def _record_to_dict(r: DFRecord) -> dict:
    return {
        "name": r.name,
        "description": r.description,
        "tags": r.tags,
        "created_at": _fmt_dt(r.created_at),
        "updated_at": _fmt_dt(r.updated_at),
        "current_version": r.current_version,
        "deleted": r.deleted,
        "versions": [_version_to_dict(v) for v in r.versions],
    }


def _record_from_dict(d: dict) -> DFRecord:
    return DFRecord(
        name=d["name"],
        description=d["description"],
        tags=d["tags"],
        created_at=_parse_dt(d["created_at"]),
        updated_at=_parse_dt(d["updated_at"]),
        current_version=d["current_version"],
        deleted=d["deleted"],
        versions=[_version_from_dict(v) for v in d.get("versions", [])],
    )


class MetadataIndex:
    def __init__(self, store_path: Path) -> None:
        self._store_path = store_path
        self._index_path = store_path / "index.json"

    def load(self) -> dict[str, DFRecord]:
        if not self._index_path.exists():
            return {}
        with open(self._index_path, encoding="utf-8") as f:
            raw = json.load(f)
        return {name: _record_from_dict(data) for name, data in raw.items()}

    def save(self, records: dict[str, DFRecord]) -> None:
        self._store_path.mkdir(parents=True, exist_ok=True)
        raw = {name: _record_to_dict(record) for name, record in records.items()}
        tmp = self._index_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._index_path)
