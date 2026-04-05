# Inspect Metadata

## info()

Get full metadata for a named DataFrame:

```python
import dfstore

r = dfstore.info("employees")
print(r)
```

Returns a single-row pandas DataFrame:

| name | description | tags | created_at | updated_at | current_version | deleted |
|---|---|---|---|---|---|---|
| employees | HR roster | hr | 2024-01-10 | 2024-02-01 | 2 | False |

---

## Raw DFRecord

```python
r = dfstore.info("employees", format="raw")

print(r.name)             # 'employees'
print(r.description)      # 'HR roster'
print(r.tags)             # ['hr', {'env': 'production'}]
print(r.created_at)       # datetime
print(r.current_version)  # 2
print(r.deleted)          # False
print(len(r.versions))    # 2 — one VersionRecord per save
```

---

## Inspecting Versions

The `DFRecord` includes the full version history:

```python
r = dfstore.info("employees", format="raw")

for v in r.versions:
    print(f"v{v.version} — {v.saved_at:%Y-%m-%d} — shape {v.shape}")
    if v.columns_added:
        print(f"  Added: {v.columns_added}")
    if v.columns_removed:
        print(f"  Removed: {v.columns_removed}")
```

---

## preview()

Load only the first few rows without pulling the full dataset:

```python
data = dfstore.preview("employees")         # first 5 rows (default)
data = dfstore.preview("employees", n=10)   # first 10 rows
data = dfstore.preview("employees", n=3, version=1)  # from v1

# Returns a plain dict — ready for JSON serialisation
print(data["columns"])  # ['name', 'age', 'department']
print(data["rows"])     # [['Alice', 25, 'Engineering'], ...]
```

This is especially useful when inspecting large datasets or building UIs.
