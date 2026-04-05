# Configuration

## Store Location

By default dfstore saves everything to **`~/.dfstore`**. There are three ways to change this.

### Environment Variable

```bash
export DFSTORE_PATH=/data/my_store
```

Any Python or CLI call will use this path automatically.

### Per-Call Argument

Every API function and CLI command accepts `--store-path` / `store_path=`:

```python
dfstore.save(df, name="data", store_path="/data/my_store")
dfstore.get("data", store_path="/data/my_store")
dfstore.list(store_path="/data/my_store")
```

```bash
dfstore save data.csv --name data --store-path /data/my_store
dfstore list --store-path /data/my_store
```

### DFStore Class

For scripts that make many calls to the same store, instantiate `DFStore` directly:

```python
from dfstore import DFStore
from pathlib import Path

store = DFStore(Path("/data/my_store"))

store.save(df, name="employees")
store.get("employees")
store.list()
```

---

## Priority Order

When resolving the store path, dfstore checks in this order:

1. `store_path` argument passed directly to the function / CLI flag
2. `DFSTORE_PATH` environment variable
3. Default: `~/.dfstore`

---

## Store Layout

```
<store_path>/
  index.json          ← all metadata (one JSON object per DataFrame)
  data/
    <name>/
      v1.parquet
      v2.parquet
      …
```

The `index.json` file is updated atomically on every save. Parquet files are never modified after creation — each save writes a new file.
