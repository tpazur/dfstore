# Delete & Restore

## Soft Delete

By default, `delete()` performs a **soft delete** — the record is hidden from `list()` and `get()`, but all data and metadata are preserved on disk.

```python
import dfstore

dfstore.delete("old_dataset")
```

The record won't appear in `dfstore.list()` after this. Attempting `dfstore.get("old_dataset")` raises `DFNotFoundError`.

---

## Checking Soft-Deleted Records

Soft-deleted records are still accessible with `include_deleted=True`:

```python
all_records = dfstore.list(include_deleted=True)

# Filter to deleted only
deleted = all_records[all_records["deleted"] == True]
print(deleted[["name", "updated_at"]])
```

---

## Restore

Undo a soft delete:

```python
dfstore.restore("old_dataset")

# Now accessible again
df = dfstore.get("old_dataset")
```

---

## Hard Delete

Permanently removes all data and metadata. **This cannot be undone.**

```python
dfstore.delete("old_dataset", hard=True)
```

After a hard delete:

- The Parquet files are removed from disk.
- The metadata entry is removed from the index.
- `restore()` will raise `DFNotFoundError`.

---

## Summary

| Action | Effect | Reversible? |
|---|---|---|
| `delete(name)` | Hides the record; data preserved | Yes — `restore()` |
| `delete(name, hard=True)` | Removes all data and metadata | No |
| `restore(name)` | Undoes a soft delete | — |
