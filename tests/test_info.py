"""Tests for dfstore.info()."""
from __future__ import annotations

import pytest

import dfstore
from dfstore.exceptions import DFNotFoundError
from dfstore.models import DFRecord


def test_info_returns_df_record_with_correct_fields(saved_employees):
    r = dfstore.info("employees", store_path=saved_employees)
    assert isinstance(r, DFRecord)
    assert r.name == "employees"
    assert r.description == "Employee roster"
    assert r.current_version == 1
    assert not r.deleted


def test_info_includes_all_version_records(store, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store)
    dfstore.save(employees_df, name="employees", store_path=store)
    r = dfstore.info("employees", store_path=store)
    assert len(r.versions) == 2


def test_info_nonexistent_raises_df_not_found(store):
    with pytest.raises(DFNotFoundError):
        dfstore.info("nonexistent", store_path=store)


def test_info_soft_deleted_still_returns_record(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    r = dfstore.info("employees", store_path=saved_employees)
    assert r.deleted is True
    assert r.name == "employees"
