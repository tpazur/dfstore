"""CLI integration tests using typer.testing.CliRunner."""
from __future__ import annotations

import json
import os

import pandas as pd
import pytest
from typer.testing import CliRunner

import dfstore
from dfstore.cli import app

runner = CliRunner()


@pytest.fixture
def parquet_file(tmp_path, employees_df):
    p = tmp_path / "employees.parquet"
    employees_df.to_parquet(p, index=False)
    return p


@pytest.fixture
def store_env(store, monkeypatch):
    monkeypatch.setenv("DFSTORE_PATH", str(store))
    return store


def test_cli_save_parquet_file_creates_record(parquet_file, store_env):
    result = runner.invoke(app, [
        "save", str(parquet_file),
        "--name", "employees",
        "--description", "Test employees",
        "--tags", "hr",
        "--tags", "env=production",
    ])
    assert result.exit_code == 0, result.output
    assert "employees" in result.output
    assert "version 1" in result.output


def test_cli_list_shows_table_headers(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Name" in result.output
    assert "employees" in result.output


def test_cli_info_shows_description_and_tags(store_env, employees_df):
    dfstore.save(employees_df, name="employees", description="Test desc",
                 tags=["hr"], store_path=store_env)
    result = runner.invoke(app, ["info", "employees"])
    assert result.exit_code == 0
    assert "Test desc" in result.output
    assert "hr" in result.output


def test_cli_get_stdout_is_valid_csv(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    result = runner.invoke(app, ["get", "employees", "--format", "csv"])
    assert result.exit_code == 0
    lines = [l for l in result.output.strip().splitlines() if l]
    assert len(lines) >= 2  # header + at least one data row
    assert "name" in lines[0].lower() or "age" in lines[0].lower()


def test_cli_search_by_description_returns_match(store_env, employees_df):
    dfstore.save(employees_df, name="employees", description="Employee roster",
                 store_path=store_env)
    result = runner.invoke(app, ["search", "--description", "roster"])
    assert result.exit_code == 0
    assert "employees" in result.output


def test_cli_search_by_tag_returns_match(store_env, employees_df):
    dfstore.save(employees_df, name="employees", tags=["hr"], store_path=store_env)
    result = runner.invoke(app, ["search", "--tags", "hr"])
    assert result.exit_code == 0
    assert "employees" in result.output


def test_cli_search_by_column_returns_match(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    result = runner.invoke(app, ["search", "--columns", "salary"])
    assert result.exit_code == 0
    assert "employees" in result.output


def test_cli_versions_shows_version_rows(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    dfstore.save(employees_df, name="employees", store_path=store_env)
    result = runner.invoke(app, ["versions", "employees"])
    assert result.exit_code == 0
    assert "1" in result.output
    assert "2" in result.output


def test_cli_delete_soft_sets_deleted(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    result = runner.invoke(app, ["delete", "employees"])
    assert result.exit_code == 0
    r = dfstore.info("employees", store_path=store_env, format="raw")
    assert r.deleted is True


def test_cli_delete_hard_with_confirmation_removes_record(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    result = runner.invoke(app, ["delete", "employees", "--hard"], input="y\n")
    assert result.exit_code == 0
    assert len(dfstore.list(include_deleted=True, store_path=store_env)) == 0


def test_cli_restore_makes_record_active(store_env, employees_df):
    dfstore.save(employees_df, name="employees", store_path=store_env)
    dfstore.delete("employees", store_path=store_env)
    result = runner.invoke(app, ["restore", "employees"])
    assert result.exit_code == 0
    r = dfstore.info("employees", store_path=store_env, format="raw")
    assert r.deleted is False


def test_cli_unknown_name_exits_nonzero(store_env):
    result = runner.invoke(app, ["info", "nonexistent"])
    assert result.exit_code != 0


def test_cli_search_no_criteria_exits_nonzero(store_env):
    result = runner.invoke(app, ["search"])
    assert result.exit_code != 0
