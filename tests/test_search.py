"""Tests for dfstore.search()."""
from __future__ import annotations

import pandas as pd
import pytest
import polars as pl

import dfstore
from dfstore.exceptions import DFNotFoundError


@pytest.fixture
def dual_store(store, employees_df, products_pl):
    dfstore.save(employees_df, name="employees", description="Company employee roster",
                 tags=["hr", "internal", {"env": "production"}], store_path=store)
    dfstore.save(products_pl, name="products", description="Product catalog from ERP",
                 tags=["inventory", {"env": "staging"}], store_path=store)
    return store


def test_search_returns_dataframe_by_default(dual_store):
    results = dfstore.search(description="catalog", store_path=dual_store)
    assert isinstance(results, pd.DataFrame)
    assert list(results.columns) == ["name", "description", "tags", "created_at", "updated_at", "current_version", "deleted"]


def test_search_by_description_substring(dual_store):
    results = dfstore.search(description="catalog", store_path=dual_store)
    assert len(results) == 1
    assert results.iloc[0]["name"] == "products"


def test_search_by_description_case_insensitive(dual_store):
    results = dfstore.search(description="CATALOG", store_path=dual_store)
    assert len(results) == 1


def test_search_by_description_no_match_returns_empty(dual_store):
    results = dfstore.search(description="zzznomatch", store_path=dual_store)
    assert isinstance(results, pd.DataFrame)
    assert len(results) == 0


def test_search_by_plain_tag(dual_store):
    results = dfstore.search(tags=["hr"], store_path=dual_store)
    assert len(results) == 1
    assert results.iloc[0]["name"] == "employees"


def test_search_by_dict_tag(dual_store):
    results = dfstore.search(tags=[{"env": "production"}], store_path=dual_store)
    assert len(results) == 1
    assert results.iloc[0]["name"] == "employees"

    results2 = dfstore.search(tags=[{"env": "staging"}], store_path=dual_store)
    assert len(results2) == 1
    assert results2.iloc[0]["name"] == "products"


def test_search_by_columns_all_must_match(dual_store):
    results = dfstore.search(columns=["price", "in_stock"], store_path=dual_store)
    assert len(results) == 1
    assert results.iloc[0]["name"] == "products"


def test_search_by_columns_partial_no_match(dual_store):
    results = dfstore.search(columns=["price", "nonexistent_col"], store_path=dual_store)
    assert len(results) == 0


def test_search_combined_description_and_tags(dual_store):
    results = dfstore.search(description="employee", tags=["hr"], store_path=dual_store)
    assert len(results) == 1
    assert results.iloc[0]["name"] == "employees"


def test_search_no_criteria_raises_value_error(dual_store):
    with pytest.raises(ValueError):
        dfstore.search(store_path=dual_store)


def test_search_excludes_soft_deleted(dual_store):
    dfstore.delete("products", store_path=dual_store)
    results = dfstore.search(tags=["inventory"], store_path=dual_store)
    assert len(results) == 0


def test_search_raw_returns_list(dual_store):
    results = dfstore.search(description="catalog", store_path=dual_store, format="raw")
    assert isinstance(results, list)
    assert results[0].name == "products"
