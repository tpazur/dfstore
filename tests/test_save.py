"""Tests for dfstore.save()."""
from __future__ import annotations

import pytest
import pandas as pd
import polars as pl

import dfstore
from dfstore.exceptions import DFStoreError
from dfstore.models import VersionRecord


def test_save_pandas_creates_parquet_file(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    assert (store / "data" / "employees" / "v1.parquet").exists()


def test_save_polars_creates_parquet_file(store, products_pl):
    dfstore.save(products_pl, name="products", store_path=store)
    assert (store / "data" / "products" / "v1.parquet").exists()


def test_save_returns_version_record(store, employees_df):
    vr = dfstore.save(employees_df, name="employees", store_path=store)
    assert isinstance(vr, VersionRecord)
    assert vr.version == 1


def test_save_creates_index_entry(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    assert (store / "index.json").exists()
    record = dfstore.info("employees", store_path=store)
    assert record.name == "employees"


def test_save_increments_version_on_resave(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    vr2 = dfstore.save(employees_df, name="employees", store_path=store)
    assert vr2.version == 2
    assert (store / "data" / "employees" / "v2.parquet").exists()


def test_save_computes_shape_diff_new_column(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    df2 = employees_df.copy()
    df2["seniority"] = [3, 7, 12, 2, 5]
    vr2 = dfstore.save(df2, name="employees", store_path=store)
    assert vr2.shape_diff == (0, 1)
    assert vr2.columns_added == ["seniority"]
    assert vr2.columns_removed == []
    assert vr2.row_diff == 0


def test_save_computes_shape_diff_new_rows(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    extra = pd.DataFrame({
        "name": ["Frank"], "age": [40], "department": ["Engineering"],
        "salary": [95000], "city": ["Seattle"],
    })
    df2 = pd.concat([employees_df, extra], ignore_index=True)
    vr2 = dfstore.save(df2, name="employees", store_path=store)
    assert vr2.row_diff == 1
    assert vr2.shape_diff == (1, 0)


def test_save_computes_columns_removed(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    df2 = employees_df.drop(columns=["city"])
    vr2 = dfstore.save(df2, name="employees", store_path=store)
    assert "city" in vr2.columns_removed
    assert vr2.shape_diff == (0, -1)


def test_save_invalid_name_raises_value_error(store, employees_df):
    with pytest.raises(ValueError, match="Invalid name"):
        dfstore.save(employees_df, name="my df!", store_path=store)


def test_save_invalid_name_with_space_raises(store, employees_df):
    with pytest.raises(ValueError):
        dfstore.save(employees_df, name="my df", store_path=store)


def test_save_on_soft_deleted_raises_df_store_error(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.delete("employees", store_path=store)
    with pytest.raises(DFStoreError, match="soft-deleted"):
        dfstore.save(employees_df, name="employees", store_path=store)


def test_save_preserves_description_on_resave(store, employees_df):
    dfstore.save(employees_df, name="employees", description="Original", store_path=store)
    dfstore.save(employees_df, name="employees", description="", store_path=store)
    record = dfstore.info("employees", store_path=store)
    assert record.description == "Original"


def test_save_updates_description_on_resave(store, employees_df):
    dfstore.save(employees_df, name="employees", description="Original", store_path=store)
    dfstore.save(employees_df, name="employees", description="Updated", store_path=store)
    record = dfstore.info("employees", store_path=store)
    assert record.description == "Updated"


def test_save_updates_tags_on_resave(store, employees_df):
    dfstore.save(employees_df, name="employees", tags=["old"], store_path=store)
    dfstore.save(employees_df, name="employees", tags=["new"], store_path=store)
    record = dfstore.info("employees", store_path=store)
    assert record.tags == ["new"]


def test_save_notes_forced_initial_save_for_v1(store, employees_df):
    vr = dfstore.save(employees_df, name="employees", notes="custom notes", store_path=store)
    assert vr.notes == "Initial save"


def test_save_empty_dataframe(store):
    df = pd.DataFrame({"a": pd.Series([], dtype="int64"), "b": pd.Series([], dtype="object")})
    vr = dfstore.save(df, name="empty", store_path=store)
    assert vr.shape == (0, 2)


def test_save_no_numeric_columns(store):
    df = pd.DataFrame({"name": ["Alice"], "city": ["NY"]})
    vr = dfstore.save(df, name="strings_only", store_path=store)
    assert vr.describe == {}


def test_save_atomic_write_no_tmp_file(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    assert not (store / "index.json.tmp").exists()


def test_save_non_dataframe_raises_type_error(store):
    with pytest.raises(TypeError):
        dfstore.save({"not": "a dataframe"}, name="bad", store_path=store)
