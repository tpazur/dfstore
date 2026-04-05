"""Tests for MetadataIndex internals."""
from __future__ import annotations

import json

import dfstore


def test_index_not_present_before_save(store):
    assert not (store / "index.json").exists()


def test_index_created_on_first_save(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    assert (store / "index.json").exists()


def test_index_is_valid_json_after_save(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    with open(store / "index.json") as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_index_schema_has_required_keys(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    with open(store / "index.json") as f:
        data = json.load(f)
    record = data["employees"]
    for key in ("name", "description", "tags", "created_at", "updated_at",
                "current_version", "deleted", "versions"):
        assert key in record, f"Missing key: {key}"
    version = record["versions"][0]
    for key in ("version", "saved_at", "notes", "shape", "columns", "dtypes",
                "null_counts", "describe", "shape_diff", "columns_added",
                "columns_removed", "row_diff", "library", "parquet_file"):
        assert key in version, f"Missing version key: {key}"


def test_index_tmp_file_removed_after_write(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    assert not (store / "index.json.tmp").exists()


def test_index_updated_on_resave(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    with open(store / "index.json") as f:
        data = json.load(f)
    assert data["employees"]["current_version"] == 2
    assert len(data["employees"]["versions"]) == 2
