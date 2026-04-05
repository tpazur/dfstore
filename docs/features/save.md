# Save & Versioning

## Basic Save

```python
import dfstore
import pandas as pd

df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

dfstore.save(df, name="my_data")
```

Every call to `save()` with the same name creates a **new version**. The old data is never overwritten.

---

## Parameters

| Parameter | Type | Description |
|---|---|---|
| `df` | `pd.DataFrame` or `pl.DataFrame` | The DataFrame to save |
| `name` | `str` | Unique name (letters, numbers, `_`, `-`; max 128 chars) |
| `description` | `str` | Optional human-readable description |
| `tags` | `list` | Optional list of tags (see below) |
| `notes` | `str` | Optional version-specific note |
| `store_path` | `Path` or `str` | Override the default store location |

---

## Adding Metadata

```python
dfstore.save(
    df,
    name="sales_2024",
    description="Annual sales data by region",
    tags=["finance", "region=EU"],
    notes="Includes Q4 revision",
)
```

---

## Tags

Tags can be plain strings or key-value pairs:

```python
# Plain string tags
dfstore.save(df, name="ds", tags=["raw", "finance"])

# Key-value dict tags
dfstore.save(df, name="ds", tags=[{"env": "production"}, {"team": "data"}])

# Mixed
dfstore.save(df, name="ds", tags=["finance", {"env": "production"}])
```

---

## Versioning

Each save increments the version counter automatically:

```python
dfstore.save(df_v1, name="dataset")   # version 1
dfstore.save(df_v2, name="dataset")   # version 2
dfstore.save(df_v3, name="dataset")   # version 3
```

The `VersionRecord` returned by `save()` contains the new version number plus diff information relative to the previous version:

```python
vr = dfstore.save(df_v2, name="dataset")

print(vr.version)          # 2
print(vr.shape)            # (100, 5)
print(vr.row_diff)         # +20 (relative to v1)
print(vr.columns_added)    # ['new_col']
print(vr.columns_removed)  # []
```

---

## Saving Polars DataFrames

dfstore works transparently with polars:

```python
import polars as pl

df = pl.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})

dfstore.save(df, name="polars_data", description="A polars DataFrame")
```

You can load it back as either pandas or polars — see [Load Data](get.md).

---

## Return Value

`save()` returns a `VersionRecord`:

```python
vr = dfstore.save(df, name="data")

vr.version         # int — version number
vr.saved_at        # datetime — UTC timestamp
vr.shape           # tuple[int, int] — (rows, cols)
vr.columns         # list[str]
vr.dtypes          # dict[str, str]
vr.null_counts     # dict[str, int]
vr.notes           # str
vr.row_diff        # int — row delta vs previous version (0 for v1)
vr.columns_added   # list[str]
vr.columns_removed # list[str]
vr.library         # 'pandas' or 'polars'
```
