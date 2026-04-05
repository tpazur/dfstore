# Load Data

## Basic Load

```python
import dfstore

df = dfstore.get("sales_2024")
```

Returns the **latest version** as the same library it was saved with (pandas or polars).

---

## Parameters

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Name of the stored DataFrame |
| `version` | `int` | Pin to a specific version (default: latest) |
| `as_library` | `"pandas"` or `"polars"` | Force output library |
| `store_path` | `Path` or `str` | Override the default store location |

---

## Load a Specific Version

```python
df_v1 = dfstore.get("sales_2024", version=1)
df_v2 = dfstore.get("sales_2024", version=2)
```

All versions are kept forever (unless hard-deleted), so you can always go back.

---

## Force a Library

Load as polars even if it was saved as pandas, and vice versa:

```python
# Always get pandas
df = dfstore.get("my_data", as_library="pandas")

# Always get polars
df = dfstore.get("my_data", as_library="polars")
```

---

## Error Handling

```python
from dfstore.exceptions import DFNotFoundError

try:
    df = dfstore.get("nonexistent")
except DFNotFoundError:
    print("DataFrame not found in store")
```

`DFNotFoundError` is raised when:

- The name doesn't exist in the store.
- The name exists but has been **hard-deleted**.
- The requested `version` number doesn't exist.
