# dfstore

[![CI](https://github.com/tpazur/dfstore/actions/workflows/ci.yml/badge.svg)](https://github.com/tpazur/dfstore/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/dfstore)](https://pypi.org/project/dfstore/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://pypi.org/project/dfstore/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/tpazur/dfstore/blob/main/LICENSE)

**dfstore** is a lightweight, serverless DataFrame storage library. Save, version, and retrieve pandas and polars DataFrames from a local store — via Python, CLI, or a web UI.

---

## Why dfstore?

Working with DataFrames across notebooks, scripts, and experiments often means wrestling with ad-hoc file naming (`data_v2_final_REAL.csv`) and no memory of what changed. dfstore solves this cleanly:

- Every `save()` creates a new **version automatically** — no naming required.
- Metadata (description, tags, shape, dtypes) is stored alongside the data.
- Load by name; optionally pin to a specific version.
- No database, no server — just **plain Parquet files** on disk.

---

## Quick Example

```python
import dfstore
import pandas as pd

df = pd.read_csv("sales.csv")

# Save
dfstore.save(df, name="sales_2024", description="Annual sales", tags=["finance"])

# Load latest
df = dfstore.get("sales_2024")

# Load a specific version
df_v1 = dfstore.get("sales_2024", version=1)
```

---

## At a Glance

| Feature | Description |
|---|---|
| **Versioning** | Every save is a new version; old versions are always accessible |
| **Diff tracking** | Row count delta, added/removed columns recorded per version |
| **pandas & polars** | Save either, load in whichever library you prefer |
| **No server needed** | Plain files on disk at `~/.dfstore` |
| **Soft delete** | Hide a DataFrame without destroying data; restore any time |
| **Web UI** | Built-in browser interface for browsing, uploading, and managing |
| **CLI** | Full command-line interface for shell scripting and pipelines |

---

## Installation

```bash
pip install dfstore          # core library + CLI
pip install 'dfstore[gui]'   # + web UI (Flask)
```
