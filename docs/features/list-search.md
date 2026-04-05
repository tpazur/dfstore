# List & Search

## List All DataFrames

```python
import dfstore

df = dfstore.list()
print(df)
```

Returns a pandas DataFrame with one row per stored entry:

| name | description | tags | created_at | updated_at | current_version | deleted |
|---|---|---|---|---|---|---|
| sales_2024 | Annual sales | finance | 2024-01-10 | 2024-03-05 | 3 | False |
| employees | HR roster | hr | 2024-02-01 | 2024-02-01 | 1 | False |

Results are sorted by `updated_at` descending (most recently updated first).

---

## Include Soft-Deleted

```python
all_records = dfstore.list(include_deleted=True)
```

---

## Raw Records

To get `DFRecord` objects instead of a DataFrame:

```python
records = dfstore.list(format="raw")

for r in records:
    print(r.name, r.current_version, r.tags)
```

---

## Search

Search across all stored DataFrames by description, tags, or column names:

=== "By description"

    ```python
    results = dfstore.search(description="sales")
    ```

=== "By tag"

    ```python
    results = dfstore.search(tags=["finance"])

    # Key-value tag
    results = dfstore.search(tags=[{"env": "production"}])
    ```

=== "By column name"

    ```python
    results = dfstore.search(columns=["revenue", "region"])
    ```

=== "Combined"

    ```python
    results = dfstore.search(
        description="sales",
        tags=["finance"],
        columns=["revenue"],
    )
    ```

All criteria are combined with **AND** — a record must match all provided filters.

---

## Search Parameters

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | Substring match against description |
| `tags` | `list` | All specified tags must be present |
| `columns` | `list[str]` | All specified column names must exist |
| `store_path` | `Path` or `str` | Override the default store location |
| `format` | `"pd"` or `"raw"` | Return as DataFrame or list of `DFRecord` |

---

## Version History

To see all versions of a specific DataFrame:

```python
vrs = dfstore.versions("sales_2024")
print(vrs)
```

Returns a DataFrame with one row per version:

| version | saved_at | notes | shape | row_diff | columns_added | columns_removed |
|---|---|---|---|---|---|---|
| 1 | 2024-01-10 | Initial | (500, 6) | 0 | [] | [] |
| 2 | 2024-02-15 | Add Q1 | (620, 6) | +120 | [] | [] |
| 3 | 2024-03-05 | Add region | (620, 7) | 0 | [region] | [] |

```python
# Raw VersionRecord objects
vrs = dfstore.versions("sales_2024", format="raw")
for v in vrs:
    print(f"v{v.version}: {v.shape}, diff={v.row_diff:+d} rows")
```
