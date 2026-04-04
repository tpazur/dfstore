"""Tests for dfstore.delete() and dfstore.restore()."""
from __future__ import annotations

import pytest
import pandas as pd

import dfstore
from dfstore.exceptions import DFNotFoundError, DFStoreError


def test_soft_delete_sets_deleted_flag_true(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    r = dfstore.info("employees", store_path=saved_employees)
    assert r.deleted is True


def test_soft_delete_hides_from_list(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    result = dfstore.list(store_path=saved_employees)
    assert result == []


def test_soft_delete_already_deleted_raises_df_store_error(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    with pytest.raises(DFStoreError, match="already deleted"):
        dfstore.delete("employees", store_path=saved_employees)


def test_hard_delete_removes_from_index(saved_employees):
    dfstore.delete("employees", hard=True, store_path=saved_employees)
    result = dfstore.list(include_deleted=True, store_path=saved_employees)
    assert result == []


def test_hard_delete_removes_parquet_directory(saved_employees):
    data_dir = saved_employees / "data" / "employees"
    assert data_dir.exists()
    dfstore.delete("employees", hard=True, store_path=saved_employees)
    assert not data_dir.exists()


def test_hard_delete_not_in_list_include_deleted(saved_employees):
    dfstore.delete("employees", hard=True, store_path=saved_employees)
    assert dfstore.list(include_deleted=True, store_path=saved_employees) == []


def test_restore_after_soft_delete_makes_active(saved_employees):
    dfstore.delete("employees", store_path=saved_employees)
    dfstore.restore("employees", store_path=saved_employees)
    r = dfstore.info("employees", store_path=saved_employees)
    assert r.deleted is False
    result = dfstore.list(store_path=saved_employees)
    assert len(result) == 1


def test_restore_not_deleted_raises_df_store_error(saved_employees):
    with pytest.raises(DFStoreError, match="not deleted"):
        dfstore.restore("employees", store_path=saved_employees)


def test_restore_nonexistent_raises_df_not_found(store):
    with pytest.raises(DFNotFoundError):
        dfstore.restore("nonexistent", store_path=store)


def test_delete_nonexistent_raises_df_not_found(store):
    with pytest.raises(DFNotFoundError):
        dfstore.delete("nonexistent", store_path=store)
