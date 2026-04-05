# Getting Started

## Installation

```bash
pip install dfstore          # core library + CLI
pip install 'dfstore[gui]'   # + web UI (requires Flask)
```

Requires Python **3.11+**.

---

## Your First Save

```python
import dfstore
import pandas as pd

df = pd.DataFrame({
    "name": ["Alice", "Bob", "Charlie"],
    "age": [25, 30, 35],
    "department": ["Engineering", "Marketing", "Engineering"],
})

vr = dfstore.save(df, name="employees", description="HR employee roster", tags=["hr"])

print(vr.version)   # 1
print(vr.shape)     # (3, 3)
```

`save()` returns a `VersionRecord` with metadata about the saved version.

---

## Load It Back

```python
df = dfstore.get("employees")
print(df)
```

---

## Where Is the Data Stored?

By default, everything is stored in **`~/.dfstore`**:

```
~/.dfstore/
  index.json          ← metadata for all DataFrames
  data/
    employees/
      v1.parquet
      v2.parquet
      …
```

You can change the location with an environment variable or per-call argument — see [Configuration](configuration.md).

---

## What's Next?

- [Save & Versioning](features/save.md) — tags, descriptions, notes, polars support
- [Load Data](features/get.md) — version pinning, library selection
- [List & Search](features/list-search.md) — browse and filter your store
- [Delete & Restore](features/delete-restore.md) — soft delete and recovery
- [Web UI](features/web-ui.md) — browser-based interface
- [CLI Reference](cli.md) — full command reference
