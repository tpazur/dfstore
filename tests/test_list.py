"""Tests for dfstore.list()."""
from __future__ import annotations

import time

import pytest
import pandas as pd

import dfstore
from dfstore.models import DFRecord


def test_list_empty_store_returns_empty_list(store):
    result = dfstore.list(store_path=store)
    assert result == []


def test_list_returns_all_active_records(store, employees_df, products_pl):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(products_pl, name="products", store_path=store)
    result = dfstore.list(store_path=store)
    names = {r.name for r in result}
    assert names == {"employees", "products"}


def test_list_excludes_soft_deleted_by_default(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.delete("employees", store_path=store)
    result = dfstore.list(store_path=store)
    assert result == []


def test_list_include_deleted_returns_soft_deleted(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.delete("employees", store_path=store)
    result = dfstore.list(include_deleted=True, store_path=store)
    assert len(result) == 1
    assert result[0].deleted is True


def test_list_sorted_by_updated_at_descending(store, employees_df):
    dfstore.save(employees_df, name="aaa", store_path=store)
    # small sleep to ensure different timestamps
    import time; time.sleep(0.05)
    dfstore.save(employees_df, name="zzz", store_path=store)
    result = dfstore.list(store_path=store)
    assert result[0].name == "zzz"
    assert result[1].name == "aaa"
