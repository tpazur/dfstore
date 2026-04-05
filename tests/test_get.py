"""Tests for dfstore.get()."""
from __future__ import annotations

import pandas as pd
import polars as pl
import pytest

import dfstore
from dfstore.exceptions import DFNotFoundError


def test_get_returns_pandas_for_pandas_saved(saved_employees):
    df = dfstore.get("employees", store_path=saved_employees)
    assert isinstance(df, pd.DataFrame)


def test_get_returns_polars_for_polars_saved(store, products_pl):
    dfstore.save(products_pl, name="products", store_path=store)
    df = dfstore.get("products", store_path=store)
    assert isinstance(df, pl.DataFrame)


def test_get_as_library_override_polars_to_pandas(store, products_pl):
    dfstore.save(products_pl, name="products", store_path=store)
    df = dfstore.get("products", as_library="pandas", store_path=store)
    assert isinstance(df, pd.DataFrame)


def test_get_as_library_override_pandas_to_polars(saved_employees):
    df = dfstore.get("employees", as_library="polars", store_path=saved_employees)
    assert isinstance(df, pl.DataFrame)


def test_get_specific_version(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    df2 = employees_df.copy()
    df2["seniority"] = [3, 7, 12, 2, 5]
    dfstore.save(df2, name="employees", store_path=store)

    v1 = dfstore.get("employees", version=1, store_path=store)
    v2 = dfstore.get("employees", version=2, store_path=store)
    assert "seniority" not in v1.columns
    assert "seniority" in v2.columns


def test_get_latest_by_default(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    df2 = employees_df.copy()
    df2["seniority"] = [1, 2, 3, 4, 5]
    dfstore.save(df2, name="employees", store_path=store)

    df = dfstore.get("employees", store_path=store)
    assert "seniority" in df.columns


def test_get_nonexistent_raises_df_not_found(store):
    with pytest.raises(DFNotFoundError):
        dfstore.get("nonexistent", store_path=store)


def test_get_soft_deleted_raises_df_not_found(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    with pytest.raises(DFNotFoundError):
        dfstore.get("employees", store_path=saved_employees)


def test_get_invalid_version_zero_raises_value_error(saved_employees):
    with pytest.raises(ValueError):
        dfstore.get("employees", version=0, store_path=saved_employees)


def test_get_invalid_version_above_current_raises_value_error(saved_employees):
    with pytest.raises(ValueError):
        dfstore.get("employees", version=99, store_path=saved_employees)


def test_get_roundtrip_data_integrity(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    df = dfstore.get("employees", store_path=store)
    pd.testing.assert_frame_equal(df.reset_index(drop=True), employees_df.reset_index(drop=True))
