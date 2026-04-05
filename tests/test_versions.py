"""Tests for dfstore.versions()."""
from __future__ import annotations

import pandas as pd
import pytest

import dfstore
from dfstore.exceptions import DFNotFoundError
from dfstore.models import VersionRecord


def test_versions_returns_dataframe_by_default(saved_employees):
    vrs = dfstore.versions("employees", store_path=saved_employees)
    assert isinstance(vrs, pd.DataFrame)
    assert list(vrs.columns) == ["version", "saved_at", "notes", "shape", "columns", "library", "shape_diff", "columns_added", "columns_removed", "row_diff"]
    assert len(vrs) == 1
    assert vrs.iloc[0]["version"] == 1


def test_versions_raw_single_version_list(saved_employees):
    vrs = dfstore.versions("employees", store_path=saved_employees, format="raw")
    assert len(vrs) == 1
    assert isinstance(vrs[0], VersionRecord)
    assert vrs[0].version == 1


def test_versions_raw_multiple_sorted_ascending(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    vrs = dfstore.versions("employees", store_path=store, format="raw")
    assert [v.version for v in vrs] == [1, 2, 3]


def test_versions_multiple_sorted_ascending(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    vrs = dfstore.versions("employees", store_path=store)
    assert list(vrs["version"]) == [1, 2, 3]


def test_versions_nonexistent_raises_df_not_found(store):
    with pytest.raises(DFNotFoundError):
        dfstore.versions("nonexistent", store_path=store)


def test_versions_shape_diff_correct_after_column_add(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    df2 = employees_df.copy()
    df2["bonus"] = [1000, 2000, 3000, 1500, 2500]
    dfstore.save(df2, name="employees", store_path=store)

    vrs = dfstore.versions("employees", store_path=store, format="raw")
    assert vrs[0].shape_diff is None
    assert vrs[1].shape_diff == (0, 1)
    assert vrs[1].columns_added == ["bonus"]


def test_versions_shape_diff_none_for_v1(saved_employees):
    vrs = dfstore.versions("employees", store_path=saved_employees, format="raw")
    assert vrs[0].shape_diff is None
