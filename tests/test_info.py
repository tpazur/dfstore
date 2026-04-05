"""Tests for dfstore.info()."""
from __future__ import annotations

import pandas as pd
import pytest

import dfstore
from dfstore.exceptions import DFNotFoundError
from dfstore.models import DFRecord


def test_info_returns_dataframe_by_default(saved_employees):
    r = dfstore.info("employees", store_path=saved_employees)
    assert isinstance(r, pd.DataFrame)
    assert list(r.columns) == ["name", "description", "tags", "created_at", "updated_at", "current_version", "deleted"]
    assert len(r) == 1
    assert r.iloc[0]["name"] == "employees"
    assert r.iloc[0]["description"] == "Employee roster"
    assert r.iloc[0]["current_version"] == 1
    assert r.iloc[0]["deleted"] == False  # noqa: E712


def test_info_raw_returns_df_record(saved_employees):
    r = dfstore.info("employees", store_path=saved_employees, format="raw")
    assert isinstance(r, DFRecord)
    assert r.name == "employees"
    assert r.description == "Employee roster"
    assert r.current_version == 1
    assert not r.deleted


def test_info_raw_includes_all_version_records(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    r = dfstore.info("employees", store_path=store, format="raw")
    assert len(r.versions) == 2


def test_info_nonexistent_raises_df_not_found(store):
    with pytest.raises(DFNotFoundError):
        dfstore.info("nonexistent", store_path=store)


def test_info_soft_deleted_still_returns_record(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    r = dfstore.info("employees", store_path=saved_employees, format="raw")
    assert r.deleted is True
    assert r.name == "employees"


def test_info_soft_deleted_df_shows_deleted_true(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    r = dfstore.info("employees", store_path=saved_employees)
    assert r.iloc[0]["deleted"] == True  # noqa: E712
