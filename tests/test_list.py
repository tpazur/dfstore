"""Tests for dfstore.list()."""
from __future__ import annotations

import time

import pandas as pd
import pytest

import dfstore
from dfstore.models import DFRecord


def test_list_empty_store_returns_empty_dataframe(store):
    result = dfstore.list(store_path=store)
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0
    assert list(result.columns) == ["name", "description", "tags", "created_at", "updated_at", "current_version", "deleted"]


def test_list_raw_empty_store_returns_empty_list(store):
    result = dfstore.list(store_path=store, format="raw")
    assert result == []


def test_list_returns_all_active_records(store, employees_df, products_pl):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(products_pl, name="products", store_path=store)
    result = dfstore.list(store_path=store)
    assert isinstance(result, pd.DataFrame)
    assert set(result["name"]) == {"employees", "products"}


def test_list_raw_returns_df_record_objects(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    result = dfstore.list(store_path=store, format="raw")
    assert isinstance(result[0], DFRecord)


def test_list_excludes_soft_deleted_by_default(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.delete("employees", store_path=store)
    result = dfstore.list(store_path=store)
    assert len(result) == 0


def test_list_include_deleted_returns_soft_deleted(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.delete("employees", store_path=store)
    result = dfstore.list(include_deleted=True, store_path=store)
    assert len(result) == 1
    assert result.iloc[0]["deleted"] == True  # noqa: E712


def test_list_sorted_by_updated_at_descending(store, employees_df):
    dfstore.save(employees_df, name="aaa", store_path=store)
    import time; time.sleep(0.05)
    dfstore.save(employees_df, name="zzz", store_path=store)
    result = dfstore.list(store_path=store)
    assert result.iloc[0]["name"] == "zzz"
    assert result.iloc[1]["name"] == "aaa"
