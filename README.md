# dfstore

[![CI](https://github.com/tpazur/dfstore/actions/workflows/ci.yml/badge.svg)](https://github.com/tpazur/dfstore/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dfstore)](https://pypi.org/project/dfstore/)
[![Python](https://img.shields.io/pypi/pyversions/dfstore)](https://pypi.org/project/dfstore/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A lightweight DataFrame storage library with rich metadata. Save, version, and retrieve pandas and polars DataFrames from a local store — via Python, CLI, or a web UI.

## Install

```bash
pip install dfstore          # core
pip install 'dfstore[gui]'   # + web UI
```

## Python API

```python
import dfstore

# Save
dfstore.save(df, name="sales_2024", description="Annual sales", tags=["finance", "region=EU"])

# Load
df = dfstore.get("sales_2024")
df = dfstore.get("sales_2024", version=2)   # specific version

# Explore
dfstore.list()
dfstore.info("sales_2024")
dfstore.versions("sales_2024")
dfstore.search(description="sales", tags=["finance"])

# Delete / restore
dfstore.delete("sales_2024")          # soft delete
dfstore.delete("sales_2024", hard=True)
dfstore.restore("sales_2024")
```

By default the store lives at `~/.dfstore`. Override with the `DFSTORE_PATH` env var or pass `store_path=` to any function.

## CLI

```bash
dfstore save data.csv --name sales_2024 --description "Annual sales" --tags finance --tags region=EU
dfstore get sales_2024
dfstore list
dfstore info sales_2024
dfstore versions sales_2024
dfstore search --description "sales" --tags finance
dfstore delete sales_2024
dfstore restore sales_2024
```

## Web UI

```bash
dfstore serve            # opens at http://127.0.0.1:7860
dfstore serve --port 8080 --host 0.0.0.0
```

Four tabs: **Browse** (filter, click a row to see version history and a data preview), **Save** (upload CSV/Parquet), **Search** (by description, tags, or column names), **Manage** (soft/hard delete and restore).

## Features

- **Versioned** — every save creates a new version; old versions are always accessible
- **Diff tracking** — row count delta, added/removed columns recorded per version
- **pandas & polars** — stores either, returns in whichever library you ask for
- **No server required** — plain files on disk (`~/.dfstore`), no database
- **Soft delete** — hides a DataFrame without removing data; restore at any time
