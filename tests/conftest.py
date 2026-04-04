"""Shared fixtures for dfstore tests."""
from __future__ import annotations

import pytest
import pandas as pd
import polars as pl

import dfstore


@pytest.fixture
def store(tmp_path):
    """Isolated store directory per test."""
    return tmp_path


@pytest.fixture
def employees_df():
    return pd.DataFrame({
        "name":       ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "age":        [25, 30, 35, 28, 32],
        "department": ["Engineering", "Marketing", "Engineering", "HR", "Marketing"],
        "salary":     [90000, 65000, 110000, 72000, 68000],
        "city":       ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    })


@pytest.fixture
def products_pl():
    return pl.DataFrame({
        "product_id":   [101, 102, 103, 104],
        "product_name": ["Widget A", "Widget B", "Gadget X", "Gadget Y"],
        "price":        [9.99, 14.99, 49.99, 79.99],
        "in_stock":     [True, True, False, True],
        "category":     ["Widget", "Widget", "Gadget", "Gadget"],
    })


@pytest.fixture
def saved_employees(store, employees_df):
    """Pre-saves employees_df into the store; returns store path."""
    dfstore.save(
        employees_df,
        name="employees",
        description="Employee roster",
        tags=["hr", {"env": "production"}],
        store_path=store,
    )
    return store
