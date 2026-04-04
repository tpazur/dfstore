# claude.md.spec — dfstore

> **Golden specification document.** This file drives implementation, test generation, README authoring, and documentation. All implementation decisions must be consistent with this spec. The Demo section (§8) is the canonical source of truth for expected behavior.

---

## 1. Project Metadata

| Field | Value |
|---|---|
| **Name** | dfstore |
| **Purpose** | Centralized DataFrame storage for solo data scientists. Save, version, retrieve, and search pandas and polars DataFrames with rich metadata. Local-first, no server required for core operations. |
| **Python** | 3.11+ |
| **Default store path** | `$HOME/.dfstore` (overridable via `DFSTORE_PATH` env var or `store_path` argument) |
| **License** | MIT |

### Dependencies

```toml
[project.dependencies]
pandas = ">=2.0"
polars = ">=0.20"
pyarrow = ">=14.0"       # parquet serialization for both pandas and polars
typer = {version = ">=0.12", extras = ["all"]}  # CLI with rich integration
rich = ">=13.0"          # terminal formatting

[project.optional-dependencies]
gui = ["gradio>=4.0"]    # web UI via `dfstore serve`

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.4",
    "mypy>=1.9",
]
```

**Rationale for Gradio:** Provides a complete web UI with zero frontend code. Correct trade-off for a solo data scientist tool — no React, no templates. Made optional to keep the core install lean.

**Rationale for Typer + Rich:** Modern, type-annotated CLI framework; Rich gives beautiful terminal tables and panels with no extra effort.

---

## 2. Architecture

### 2.1 Package Structure

```
dfstore/
├── pyproject.toml
├── README.md
├── claude.md.spec
├── human.spec.md
│
├── src/
│   └── dfstore/
│       ├── __init__.py      # public API: save, get, list, info, search, versions, delete, restore
│       ├── store.py         # DFStore class — all business logic
│       ├── metadata.py      # MetadataIndex: read/write index.json atomically
│       ├── storage.py       # StorageBackend: parquet read/write for pandas and polars
│       ├── models.py        # DFRecord, VersionRecord dataclasses
│       ├── diff.py          # shape/column diff between two VersionRecords
│       ├── cli.py           # Typer CLI app
│       ├── gui.py           # Gradio web UI (requires optional [gui] extra)
│       └── exceptions.py    # DFStoreError, DFNotFoundError, DFNameConflictError
│
└── tests/
    ├── conftest.py
    ├── test_save.py
    ├── test_get.py
    ├── test_list.py
    ├── test_info.py
    ├── test_search.py
    ├── test_versions.py
    ├── test_delete.py
    ├── test_cli.py
    └── test_metadata.py
```

### 2.2 Storage Layout

All data lives under `$HOME/.dfstore` by default.

```
~/.dfstore/
├── index.json                   # single metadata index (all records, all versions)
└── data/
    └── {name}/
        ├── v1.parquet
        ├── v2.parquet
        └── ...
```

**index.json is the single source of truth for all metadata.** `list()`, `search()`, and `versions()` only read this file — no filesystem traversal. Parquet files are immutable once written; a new save always appends a new version file, never overwrites.

### 2.3 Metadata Schema

#### index.json top-level structure

```json
{
  "employees": { "...DFRecord..." },
  "products":  { "...DFRecord..." }
}
```

#### DFRecord (per DataFrame name)

```json
{
  "name": "employees",
  "description": "Company employee roster",
  "tags": ["hr", "internal", {"env": "production"}],
  "created_at": "2024-06-01T10:00:00Z",
  "updated_at": "2024-06-02T09:30:00Z",
  "current_version": 2,
  "deleted": false,
  "versions": ["...VersionRecord array..."]
}
```

#### VersionRecord (one element per version in `versions` array)

```json
{
  "version": 2,
  "saved_at": "2024-06-02T09:30:00Z",
  "notes": "Annual raise + seniority column added",
  "shape": [5, 6],
  "columns": ["name", "age", "department", "salary", "city", "seniority"],
  "dtypes": {
    "name": "object", "age": "int64", "department": "object",
    "salary": "int64", "city": "object", "seniority": "int64"
  },
  "null_counts": {"name": 0, "age": 0, "department": 0, "salary": 0, "city": 0, "seniority": 0},
  "describe": {
    "age":      {"count": 5.0, "mean": 30.0, "std": 3.8, "min": 25.0, "25%": 28.0, "50%": 30.0, "75%": 32.0, "max": 35.0},
    "salary":   {"count": 5.0, "mean": 90200.0, "std": 17600.0, "min": 71500.0, "25%": 74800.0, "50%": 88000.0, "75%": 99000.0, "max": 121000.0},
    "seniority":{"count": 5.0, "mean": 5.8, "std": 3.7, "min": 2.0, "25%": 3.0, "50%": 5.0, "75%": 7.0, "max": 12.0}
  },
  "shape_diff": [0, 1],
  "columns_added": ["seniority"],
  "columns_removed": [],
  "row_diff": 0,
  "library": "pandas",
  "parquet_file": "data/employees/v2.parquet"
}
```

**Field notes:**
- `shape_diff`: `null` for v1; for v2+ it is `[row_delta, col_delta]` relative to the prior version.
- `columns_added` / `columns_removed`: column names that changed relative to the prior version.
- `row_diff`: integer delta of rows vs prior version (positive = added, negative = removed).
- `library`: `"pandas"` or `"polars"` — recorded at save time; `get()` uses this to determine the return type unless overridden.
- `describe`: numeric columns only. Non-numeric columns are omitted. Empty dict `{}` when no numeric columns exist.
- `notes`: per-version free text. Defaults to `"Initial save"` for v1 (regardless of user input).
- `parquet_file`: path relative to the store root.

### 2.4 Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Data format | Parquet | Preserves dtypes, efficient columnar storage, pyarrow handles both pandas and polars |
| Metadata format | Single `index.json` | Human-readable, fast for small collections (< thousands), zero database dependency |
| Versioning strategy | Immutable append-only parquet files | Simple, no data loss, files are inspectable manually |
| Library detection | `isinstance` at save/get time | No user declaration required |
| Soft delete | `deleted: true` flag in `index.json` | Hides from `list()`/`search()` by default; fully recoverable via `restore()` |
| Hard delete | Remove index entry + `shutil.rmtree` on data dir | Irreversible; requires explicit `hard=True` |
| Atomic writes | Write to `.index.json.tmp`, then `os.replace()` | POSIX atomic rename; prevents index corruption on crash |
| Store override | `DFSTORE_PATH` env var or `store_path` argument | Enables testing and multi-environment use |
| CLI framework | Typer + Rich | Modern, annotated, built-in help generation |
| GUI framework | Gradio | Zero frontend code, optional install |

---

## 3. API Spec

All public functions are importable from `dfstore`:

```python
import dfstore
```

They are thin wrappers over a `DFStore` instance. Store path resolution order: explicit `store_path` argument > `DFSTORE_PATH` env var > `$HOME/.dfstore`.

---

### 3.1 `save`

```python
def save(
    df: pd.DataFrame | pl.DataFrame,
    name: str,
    description: str = '',
    tags: list[str | dict[str, str]] | None = None,
    notes: str = '',
    store_path: str | Path | None = None,
) -> VersionRecord:
```

**Parameters:**
- `df` — pandas or polars DataFrame.
- `name` — unique identifier. Must match `^[a-zA-Z0-9_\-]{1,128}$`. Raises `ValueError` if invalid.
- `description` — human-readable description. Stored on v1; preserved on re-save if empty string is passed.
- `tags` — list of plain strings and/or single-key dicts (e.g. `['hr', {'env': 'production'}]`). Replaces the entire tag list on every save.
- `notes` — per-version note. Forced to `"Initial save"` for v1 regardless of input.
- `store_path` — override store directory for this call.

**Behavior:**
1. Validate `name`; raise `ValueError` on failure.
2. Validate `df` is `pd.DataFrame` or `pl.DataFrame`; raise `TypeError` otherwise.
3. Create store directories if they do not exist (`~/.dfstore/data/{name}/`).
4. Detect library from `isinstance`.
5. Compute metadata: shape, columns, dtypes, null_counts, describe (numeric cols only).
6. **New name:** create `DFRecord` at v1, write `data/{name}/v1.parquet`, set notes to `"Initial save"`.
7. **Existing name, not deleted:** increment version, compute diff vs prior version, write `data/{name}/v{N}.parquet`, append `VersionRecord`, update `updated_at` and `current_version`. Update `description` only if a non-empty string was passed.
8. **Existing name, deleted:** raise `DFStoreError(f"'{name}' is soft-deleted. Restore it first or use a different name.")`.
9. Write `index.json` atomically.
10. Return the new `VersionRecord`.

**Errors:** `ValueError` (bad name), `TypeError` (bad df type), `DFStoreError` (soft-deleted name).

---

### 3.2 `get`

```python
def get(
    name: str,
    version: int | None = None,
    as_library: Literal['pandas', 'polars'] | None = None,
    store_path: str | Path | None = None,
) -> pd.DataFrame | pl.DataFrame:
```

**Parameters:**
- `name` — DataFrame name.
- `version` — specific version to retrieve; `None` = latest.
- `as_library` — force return type; `None` = same library as saved.
- `store_path` — override store directory.

**Behavior:**
1. Look up `name` in `index.json`. Raise `DFNotFoundError` if absent or `deleted == true`.
2. Resolve version: if `None`, use `current_version`. Validate `1 <= version <= current_version`; raise `ValueError` if out of range.
3. Read the parquet file at `VersionRecord.parquet_file`.
4. Return as the appropriate library type based on `as_library` or the saved `library` field.

**Errors:** `DFNotFoundError`, `ValueError` (bad version).

---

### 3.3 `list`

```python
def list(
    include_deleted: bool = False,
    store_path: str | Path | None = None,
) -> list[DFRecord]:
```

**Behavior:**
1. Read `index.json`. Return `[]` if file does not exist or store is empty.
2. Filter out `deleted == true` records unless `include_deleted=True`.
3. Return sorted by `updated_at` descending.

**Errors:** None — empty store returns `[]`.

> **Implementation note:** The public function is named `list` which shadows Python's builtin. Inside `store.py`, use `builtins.list` or construct lists via `[]` literals to avoid collision.

---

### 3.4 `info`

```python
def info(
    name: str,
    store_path: str | Path | None = None,
) -> DFRecord:
```

**Behavior:**
1. Look up `name` in `index.json`. Raise `DFNotFoundError` if absent.
2. Return the full `DFRecord` (including soft-deleted records — `info` is allowed on deleted items).

**Errors:** `DFNotFoundError`.

---

### 3.5 `search`

```python
def search(
    description: str | None = None,
    tags: list[str | dict[str, str]] | None = None,
    columns: list[str] | None = None,
    store_path: str | Path | None = None,
) -> list[DFRecord]:
```

**Parameters:**
- `description` — case-insensitive substring match against `DFRecord.description`.
- `tags` — all items must be present in the record's tag list. Plain strings matched exactly; dict tags matched by key+value.
- `columns` — all column names must be present in the current version's `columns` list.

**Behavior:**
1. Raise `ValueError` if all three params are `None`.
2. Call `list()` to get active (non-deleted) records.
3. Apply all provided filters (AND logic — record must satisfy every non-None criterion).
4. Return sorted by `updated_at` descending.

**Errors:** `ValueError` (no criteria provided).

---

### 3.6 `versions`

```python
def versions(
    name: str,
    store_path: str | Path | None = None,
) -> list[VersionRecord]:
```

**Behavior:**
1. Look up `name`. Raise `DFNotFoundError` if absent.
2. Return `DFRecord.versions` sorted ascending by version number.

**Errors:** `DFNotFoundError`.

---

### 3.7 `delete`

```python
def delete(
    name: str,
    hard: bool = False,
    store_path: str | Path | None = None,
) -> None:
```

**Soft delete (`hard=False`):**
1. Look up `name`. Raise `DFNotFoundError` if absent.
2. If already `deleted == true`: raise `DFStoreError(f"'{name}' is already deleted.")`.
3. Set `deleted = true`; write atomically.

**Hard delete (`hard=True`):**
1. Look up `name`. Raise `DFNotFoundError` if absent.
2. Remove entry from `index.json`.
3. Delete `data/{name}/` via `shutil.rmtree`.
4. Write updated `index.json` atomically.

**Errors:** `DFNotFoundError`, `DFStoreError` (already soft-deleted).

---

### 3.8 `restore`

```python
def restore(
    name: str,
    store_path: str | Path | None = None,
) -> None:
```

**Behavior:**
1. Look up `name`. Raise `DFNotFoundError` if absent.
2. If `deleted == false`: raise `DFStoreError(f"'{name}' is not deleted.")`.
3. Set `deleted = false`; write atomically.

**Errors:** `DFNotFoundError`, `DFStoreError` (not deleted).

---

## 4. Models

`src/dfstore/models.py` — canonical data types used throughout the codebase.

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VersionRecord:
    version: int
    saved_at: datetime
    notes: str
    shape: tuple[int, int]
    columns: list[str]
    dtypes: dict[str, str]
    null_counts: dict[str, int]
    describe: dict[str, dict[str, float]]
    shape_diff: tuple[int, int] | None    # None for v1
    columns_added: list[str]
    columns_removed: list[str]
    row_diff: int
    library: str                          # 'pandas' or 'polars'
    parquet_file: str                     # relative path from store root


@dataclass
class DFRecord:
    name: str
    description: str
    tags: list[str | dict[str, str]]
    created_at: datetime
    updated_at: datetime
    current_version: int
    deleted: bool
    versions: list[VersionRecord] = field(default_factory=list)
```

---

## 5. Exceptions

`src/dfstore/exceptions.py`:

```python
class DFStoreError(Exception):
    """Base exception for all dfstore errors."""

class DFNotFoundError(DFStoreError):
    """Raised when a DataFrame name is not found in the store."""

class DFNameConflictError(DFStoreError):
    """Reserved for future concurrent-write conflict detection."""
```

All three are re-exported from `dfstore/__init__.py` so users can catch them as `dfstore.DFNotFoundError`.

---

## 6. CLI Spec

Entry point: `dfstore` (configured in `pyproject.toml` `[project.scripts]`).

All subcommands accept `--store-path PATH` to override the store directory.

Output: Rich tables for list/search/versions; Rich panels for info; plain messages for single-action commands.

---

### 6.1 `dfstore save`

```
dfstore save FILE --name NAME [--description TEXT] [--tags TAG]... [--notes TEXT]
```

- `FILE`: path to a `.parquet` or `.csv` file. Use `-` to read parquet from stdin.
- `--name NAME` (required)
- `--tags TAG`: repeatable. `demo` → plain string tag. `env=production` → dict tag `{'env': 'production'}`.

**Success output:**
```
Saved 'employees' version 1 (5 rows × 5 cols)
```

---

### 6.2 `dfstore get`

```
dfstore get NAME [--version N] [--output PATH] [--format parquet|csv|json]
```

- Default format: `csv` printed to stdout.
- With `--output PATH`: writes file and prints `Written to employees.csv`.

---

### 6.3 `dfstore list`

```
dfstore list [--include-deleted]
```

**Output:** Rich table.

```
┌───────────┬─────────────────────────┬──────────────────────────┬─────────────────────┬─────────┬────────┐
│ Name      │ Description             │ Tags                     │ Last Updated        │ Version │ Shape  │
├───────────┼─────────────────────────┼──────────────────────────┼─────────────────────┼─────────┼────────┤
│ employees │ Company employee roster │ hr, internal, env=prod.. │ 2024-06-02 09:30:00 │ 2       │ (5, 6) │
│ products  │ Product catalog from .. │ inventory, env=staging   │ 2024-06-01 10:00:00 │ 1       │ (4, 5) │
└───────────┴─────────────────────────┴──────────────────────────┴─────────────────────┴─────────┴────────┘
```

Tags rendered: plain strings as-is; dict tags as `key=value`.

---

### 6.4 `dfstore info`

```
dfstore info NAME
```

**Output:** Rich panel.

```
╭──────────────────────── employees ────────────────────────╮
│ Description : Company employee roster                      │
│ Tags        : hr, internal, env=production                 │
│ Created     : 2024-06-01 10:00:00                          │
│ Updated     : 2024-06-02 09:30:00                          │
│ Version     : 2                                            │
│ Shape       : (5, 6)                                       │
│ Deleted     : No                                           │
├────────────────────────────────────────────────────────────┤
│ Columns & Dtypes (current version)                         │
│   name         object                                      │
│   age          int64                                       │
│   department   object                                      │
│   salary       int64                                       │
│   city         object                                      │
│   seniority    int64                                       │
├────────────────────────────────────────────────────────────┤
│ Null Counts                                                │
│   name: 0  age: 0  department: 0  salary: 0  city: 0       │
│   seniority: 0                                             │
╰────────────────────────────────────────────────────────────╯
```

---

### 6.5 `dfstore search`

```
dfstore search [--description TEXT] [--tags TAG]... [--columns COL]...
```

At least one option required; exits with code 1 and prints error if none provided.

Output: same Rich table as `dfstore list`. Prints `No results found.` for empty results.

---

### 6.6 `dfstore versions`

```
dfstore versions NAME
```

**Output:** Rich table.

```
┌─────────┬─────────────────────┬──────────────────────────────────┬────────┬──────────┬─────────────────┬──────────────────┐
│ Version │ Saved At            │ Notes                            │ Shape  │ Row Diff │ Cols Added      │ Cols Removed     │
├─────────┼─────────────────────┼──────────────────────────────────┼────────┼──────────┼─────────────────┼──────────────────┤
│ 1       │ 2024-06-01 10:00:00 │ Initial load from HR system      │ (5, 5) │ —        │ —               │ —                │
│ 2       │ 2024-06-02 09:30:00 │ Annual raise + seniority added   │ (5, 6) │ 0        │ seniority       │ —                │
└─────────┴─────────────────────┴──────────────────────────────────┴────────┴──────────┴─────────────────┴──────────────────┘
```

---

### 6.7 `dfstore delete`

```
dfstore delete NAME [--hard]
```

- **Soft delete** (default): `'employees' has been soft-deleted. Use 'dfstore restore employees' to recover it.`
- **Hard delete**: prompts `Are you sure you want to permanently delete 'employees' and all N versions? [y/N]`. On `y`: `'employees' has been permanently deleted.`

---

### 6.8 `dfstore restore`

```
dfstore restore NAME
```

Output: `'employees' has been restored.`

---

### 6.9 `dfstore serve`

```
dfstore serve [--port PORT] [--host HOST]
```

- `--port`: default `7860`
- `--host`: default `127.0.0.1`

Output: `dfstore UI running at http://127.0.0.1:7860` then starts Gradio in blocking mode.

---

## 7. GUI Spec

Implemented in `gui.py` using `gradio.Blocks`. Single-page tabbed interface, four tabs.

### Tab 1: Browse (default)

**Components:**
- Text input (search bar) — live-filters table by name or description.
- Checkbox: "Include deleted".
- Refresh button.
- `gr.Dataframe` table: Name, Description, Tags, Last Updated, Version, Shape.
- Info panel (key-value) for the selected row.
- Version dropdown — select which version to preview.
- "Load Data" button — loads the selected DF (first 100 rows) into a `gr.Dataframe` preview.

### Tab 2: Save

**Components:**
- `gr.File` upload — accepts `.parquet` and `.csv`.
- Text inputs: Name (required), Description, Tags (comma-separated; `key=value` for dict tags), Notes.
- "Save" button.
- Status message output (success or error text).

**Behavior:** Auto-detect format from file extension; read as pandas; call `dfstore.save()`.

### Tab 3: Search

**Components:**
- Text inputs: Description contains, Tags (comma-separated), Columns (comma-separated).
- "Search" button.
- Results table (same format as Browse tab).

### Tab 4: Manage

**Components:**
- Dropdown: select a DataFrame name (populated on tab open).
- "Soft Delete" button + confirmation checkbox ("I understand this will hide the DataFrame").
- "Hard Delete" button + confirmation checkbox ("I understand this is permanent and irreversible").
- "Restore" button (only active when selected item is soft-deleted).
- Status message output.

---

## 8. Demo

> **This section is the canonical source of truth for expected behavior.** It is used to generate unit/integration tests, the README showcase, and multipage HTML documentation. The `assert` statements define invariants that tests must replicate in isolation.

```python
"""
dfstore — full feature demo
Run standalone: python demo.py
Requires: pip install dfstore

Uses a temporary directory as the store so it is self-contained and repeatable.
"""
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import polars as pl

import dfstore

# ── Setup ──────────────────────────────────────────────────────────────────────
DEMO_STORE = Path(tempfile.mkdtemp(prefix="dfstore_demo_"))
print(f"Demo store: {DEMO_STORE}\n")


# ── 1. SAVE — pandas DataFrame ─────────────────────────────────────────────────
employees = pd.DataFrame({
    'name':       ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
    'age':        [25, 30, 35, 28, 32],
    'department': ['Engineering', 'Marketing', 'Engineering', 'HR', 'Marketing'],
    'salary':     [90000, 65000, 110000, 72000, 68000],
    'city':       ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
})

record = dfstore.save(
    employees,
    name='employees',
    description='Company employee roster',
    tags=['hr', 'internal', {'env': 'production'}],
    notes='Initial load from HR system',
    store_path=DEMO_STORE,
)
print(f"[1] Saved 'employees' v{record.version}: shape={record.shape}")
assert record.version == 1
assert record.shape == (5, 5)
assert record.library == 'pandas'
assert record.notes == 'Initial save'  # forced for v1 regardless of input
# Expected: [1] Saved 'employees' v1: shape=(5, 5)


# ── 2. SAVE — polars DataFrame ─────────────────────────────────────────────────
products = pl.DataFrame({
    'product_id':   [101, 102, 103, 104],
    'product_name': ['Widget A', 'Widget B', 'Gadget X', 'Gadget Y'],
    'price':        [9.99, 14.99, 49.99, 79.99],
    'in_stock':     [True, True, False, True],
    'category':     ['Widget', 'Widget', 'Gadget', 'Gadget'],
})

record2 = dfstore.save(
    products,
    name='products',
    description='Product catalog from ERP',
    tags=['inventory', {'env': 'staging'}],
    store_path=DEMO_STORE,
)
print(f"[2] Saved 'products' v{record2.version}: shape={record2.shape}, library={record2.library}")
assert record2.version == 1
assert record2.shape == (4, 5)
assert record2.library == 'polars'
# Expected: [2] Saved 'products' v1: shape=(4, 5), library=polars


# ── 3. INFO ────────────────────────────────────────────────────────────────────
info = dfstore.info('employees', store_path=DEMO_STORE)
print(f"\n[3] Info for 'employees':")
print(f"    Description : {info.description}")
print(f"    Tags        : {info.tags}")
print(f"    Version     : {info.current_version}")
print(f"    Shape       : {info.versions[-1].shape}")
print(f"    Columns     : {info.versions[-1].columns}")
assert info.description == 'Company employee roster'
assert info.current_version == 1
assert info.versions[-1].shape == (5, 5)
assert set(info.versions[-1].columns) == {'name', 'age', 'department', 'salary', 'city'}
assert not info.deleted


# ── 4. GET — latest version (pandas) ──────────────────────────────────────────
df = dfstore.get('employees', store_path=DEMO_STORE)
print(f"\n[4] Get 'employees' (pandas): shape={df.shape}, type={type(df).__name__}")
assert isinstance(df, pd.DataFrame)
assert df.shape == (5, 5)
assert list(df['name']) == ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']


# ── 5. GET — polars roundtrip ──────────────────────────────────────────────────
pl_df = dfstore.get('products', store_path=DEMO_STORE)
print(f"[5] Get 'products' (polars): shape={pl_df.shape}, type={type(pl_df).__name__}")
assert isinstance(pl_df, pl.DataFrame)
assert pl_df.shape == (4, 5)


# ── 6. GET — cross-library conversion ─────────────────────────────────────────
pd_from_polars = dfstore.get('products', as_library='pandas', store_path=DEMO_STORE)
print(f"[6] Get 'products' as pandas: type={type(pd_from_polars).__name__}")
assert isinstance(pd_from_polars, pd.DataFrame)
assert pd_from_polars.shape == (4, 5)


# ── 7. LIST ────────────────────────────────────────────────────────────────────
all_records = dfstore.list(store_path=DEMO_STORE)
print(f"\n[7] List — {len(all_records)} DataFrames stored:")
for r in all_records:
    print(f"    {r.name:15s} v{r.current_version}  {r.description}")
assert len(all_records) == 2
names = [r.name for r in all_records]
assert 'employees' in names and 'products' in names


# ── 8. VERSIONING — update employees ──────────────────────────────────────────
employees_v2 = employees.copy()
employees_v2['salary'] = (employees_v2['salary'] * 1.10).astype(int)
employees_v2['seniority'] = [3, 7, 12, 2, 5]

record_v2 = dfstore.save(
    employees_v2,
    name='employees',
    notes='Annual raise + seniority column added',
    store_path=DEMO_STORE,
)
print(f"\n[8] Saved 'employees' v{record_v2.version}")
print(f"    shape_diff      = {record_v2.shape_diff}")
print(f"    columns_added   = {record_v2.columns_added}")
print(f"    columns_removed = {record_v2.columns_removed}")
print(f"    row_diff        = {record_v2.row_diff}")
assert record_v2.version == 2
assert record_v2.shape_diff == (0, 1)   # same rows, one new column
assert record_v2.columns_added == ['seniority']
assert record_v2.columns_removed == []
assert record_v2.row_diff == 0
# Description preserved from v1 when not re-specified
assert dfstore.info('employees', store_path=DEMO_STORE).description == 'Company employee roster'


# ── 9. VERSIONS ────────────────────────────────────────────────────────────────
version_history = dfstore.versions('employees', store_path=DEMO_STORE)
print(f"\n[9] Version history for 'employees' ({len(version_history)} versions):")
for v in version_history:
    diff = f"shape_diff={v.shape_diff}" if v.shape_diff is not None else "initial"
    print(f"    v{v.version}  '{v.notes}'  {diff}")
assert len(version_history) == 2
assert version_history[0].version == 1
assert version_history[1].version == 2
assert version_history[0].shape_diff is None
assert version_history[1].shape_diff == (0, 1)


# ── 10. GET specific version ───────────────────────────────────────────────────
df_v1 = dfstore.get('employees', version=1, store_path=DEMO_STORE)
df_v2 = dfstore.get('employees', version=2, store_path=DEMO_STORE)
print(f"\n[10] employees v1 cols={list(df_v1.columns)}")
print(f"     employees v2 cols={list(df_v2.columns)}")
assert df_v1.shape == (5, 5)
assert df_v2.shape == (5, 6)
assert 'seniority' not in df_v1.columns
assert 'seniority' in df_v2.columns
assert df_v1['salary'].sum() < df_v2['salary'].sum()  # v2 has raised salaries


# ── 11. SEARCH — by description ────────────────────────────────────────────────
results = dfstore.search(description='catalog', store_path=DEMO_STORE)
print(f"\n[11] Search description='catalog': {[r.name for r in results]}")
assert len(results) == 1
assert results[0].name == 'products'

results_case = dfstore.search(description='CATALOG', store_path=DEMO_STORE)
assert len(results_case) == 1  # case-insensitive


# ── 12. SEARCH — by tags ───────────────────────────────────────────────────────
results = dfstore.search(tags=['hr'], store_path=DEMO_STORE)
print(f"[12] Search tags=['hr']: {[r.name for r in results]}")
assert len(results) == 1 and results[0].name == 'employees'

results = dfstore.search(tags=[{'env': 'production'}], store_path=DEMO_STORE)
print(f"     Search tags=[{{'env':'production'}}]: {[r.name for r in results]}")
assert len(results) == 1 and results[0].name == 'employees'

results = dfstore.search(tags=[{'env': 'staging'}], store_path=DEMO_STORE)
assert len(results) == 1 and results[0].name == 'products'


# ── 13. SEARCH — by columns ────────────────────────────────────────────────────
results = dfstore.search(columns=['seniority'], store_path=DEMO_STORE)
print(f"[13] Search columns=['seniority']: {[r.name for r in results]}")
assert len(results) == 1 and results[0].name == 'employees'

results = dfstore.search(columns=['price', 'in_stock'], store_path=DEMO_STORE)
print(f"     Search columns=['price','in_stock']: {[r.name for r in results]}")
assert len(results) == 1 and results[0].name == 'products'

results_none = dfstore.search(columns=['nonexistent_col'], store_path=DEMO_STORE)
assert len(results_none) == 0


# ── 14. SOFT DELETE ────────────────────────────────────────────────────────────
dfstore.delete('products', hard=False, store_path=DEMO_STORE)
active = dfstore.list(store_path=DEMO_STORE)
all_including_deleted = dfstore.list(include_deleted=True, store_path=DEMO_STORE)
print(f"\n[14] After soft-delete of 'products':")
print(f"     list()                      → {len(active)} records")
print(f"     list(include_deleted=True)  → {len(all_including_deleted)} records")
assert len(active) == 1
assert len(all_including_deleted) == 2

# info() still works on soft-deleted
info_deleted = dfstore.info('products', store_path=DEMO_STORE)
assert info_deleted.deleted is True

# get() raises for soft-deleted
try:
    dfstore.get('products', store_path=DEMO_STORE)
    assert False, "Should have raised DFNotFoundError"
except dfstore.DFNotFoundError:
    print("     get() raises DFNotFoundError for soft-deleted item ✓")

# search() excludes soft-deleted
search_results = dfstore.search(tags=['inventory'], store_path=DEMO_STORE)
assert len(search_results) == 0


# ── 15. RESTORE ────────────────────────────────────────────────────────────────
dfstore.restore('products', store_path=DEMO_STORE)
active_after_restore = dfstore.list(store_path=DEMO_STORE)
print(f"\n[15] After restore: {len(active_after_restore)} active records")
assert len(active_after_restore) == 2
assert dfstore.info('products', store_path=DEMO_STORE).deleted is False


# ── 16. HARD DELETE ────────────────────────────────────────────────────────────
dfstore.delete('products', hard=True, store_path=DEMO_STORE)
final = dfstore.list(include_deleted=True, store_path=DEMO_STORE)
print(f"\n[16] After hard delete: {len(final)} records total")
assert len(final) == 1
assert not (DEMO_STORE / 'data' / 'products').exists()

# Completely gone — info raises too
try:
    dfstore.info('products', store_path=DEMO_STORE)
    assert False, "Should have raised DFNotFoundError"
except dfstore.DFNotFoundError:
    print("     info() raises DFNotFoundError after hard delete ✓")


# ── Error cases ────────────────────────────────────────────────────────────────
# Invalid name
try:
    dfstore.save(employees, name='my df!', store_path=DEMO_STORE)
    assert False
except ValueError as e:
    print(f"\n[err] Invalid name raises ValueError: {e}")

# Wrong type
try:
    dfstore.save({'not': 'a dataframe'}, name='bad', store_path=DEMO_STORE)
    assert False
except TypeError as e:
    print(f"[err] Non-DataFrame raises TypeError: {e}")

# Search with no criteria
try:
    dfstore.search(store_path=DEMO_STORE)
    assert False
except ValueError as e:
    print(f"[err] search() with no criteria raises ValueError: {e}")


# ── Cleanup ────────────────────────────────────────────────────────────────────
shutil.rmtree(DEMO_STORE)
print(f"\nDemo complete. Temporary store cleaned up.")
```

---

## 9. CLI Demo

```bash
#!/usr/bin/env bash
# Requires dfstore installed: pip install dfstore
# Uses a temp store to avoid touching ~/.dfstore
export DFSTORE_PATH=$(mktemp -d)
echo "CLI demo store: $DFSTORE_PATH"

# Create a parquet file to save via CLI
python -c "
import pandas as pd
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age':  [25, 30, 35],
    'city': ['New York', 'Los Angeles', 'Chicago'],
})
df.to_parquet('/tmp/mydf.parquet', index=False)
"

# Save
dfstore save /tmp/mydf.parquet \
    --name mydf \
    --description "Sample dataframe" \
    --tags demo \
    --tags env=production \
    --notes "CLI demo save"

# List
dfstore list

# Info
dfstore info mydf

# Get as CSV (stdout)
dfstore get mydf

# Get as CSV to file
dfstore get mydf --output /tmp/mydf_out.csv --format csv

# Version history
dfstore versions mydf

# Search
dfstore search --description "Sample"
dfstore search --tags demo
dfstore search --columns age

# Soft delete and restore
dfstore delete mydf
dfstore list --include-deleted
dfstore restore mydf

# Hard delete (non-interactive: pipe 'y')
echo y | dfstore delete mydf --hard

# Cleanup
rm -rf "$DFSTORE_PATH"
```

---

## 10. Testing Strategy

### 10.1 Shared Fixtures (`tests/conftest.py`)

```python
import pytest
import pandas as pd
import polars as pl
import dfstore

@pytest.fixture
def store(tmp_path):
    """Isolated store directory per test."""
    return tmp_path

@pytest.fixture
def employees_df():
    return pd.DataFrame({
        'name':       ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
        'age':        [25, 30, 35, 28, 32],
        'department': ['Engineering', 'Marketing', 'Engineering', 'HR', 'Marketing'],
        'salary':     [90000, 65000, 110000, 72000, 68000],
        'city':       ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'],
    })

@pytest.fixture
def products_pl():
    return pl.DataFrame({
        'product_id':   [101, 102, 103, 104],
        'product_name': ['Widget A', 'Widget B', 'Gadget X', 'Gadget Y'],
        'price':        [9.99, 14.99, 49.99, 79.99],
        'in_stock':     [True, True, False, True],
        'category':     ['Widget', 'Widget', 'Gadget', 'Gadget'],
    })

@pytest.fixture
def saved_employees(store, employees_df):
    """Pre-saves employees into the store; returns store path."""
    dfstore.save(employees_df, name='employees',
                 description='Employee roster',
                 tags=['hr', {'env': 'production'}],
                 store_path=store)
    return store
```

### 10.2 Test Cases

#### `test_save.py`
- `test_save_pandas_creates_parquet_file` — parquet file exists at `data/employees/v1.parquet`.
- `test_save_polars_creates_parquet_file` — same for polars.
- `test_save_returns_version_record` — return type is `VersionRecord`, `version == 1`.
- `test_save_creates_index_entry` — `index.json` contains the record after save.
- `test_save_increments_version_on_resave` — second save produces `version == 2`.
- `test_save_computes_shape_diff_new_column` — adds a column; verifies `columns_added` and `shape_diff == (0, 1)`.
- `test_save_computes_shape_diff_new_rows` — adds rows; verifies `row_diff > 0` and `shape_diff[0] > 0`.
- `test_save_computes_columns_removed` — drops a column; verifies `columns_removed`.
- `test_save_invalid_name_raises_value_error` — name with space or `!` raises `ValueError`.
- `test_save_on_soft_deleted_raises_df_store_error`.
- `test_save_preserves_description_on_resave` — re-saving with `description=''` keeps original.
- `test_save_updates_description_on_resave` — re-saving with new description updates it.
- `test_save_updates_tags_on_resave` — new tags list replaces old.
- `test_save_notes_forced_initial_save_for_v1` — user passes custom notes; v1 notes are `"Initial save"`.
- `test_save_empty_dataframe` — zero-row DataFrame is accepted; `shape == (0, N)`.
- `test_save_no_numeric_columns` — `describe == {}`, no error.
- `test_save_atomic_write` — `index.json.tmp` does not remain after a successful save.
- `test_save_non_dataframe_raises_type_error`.

#### `test_get.py`
- `test_get_returns_pandas_for_pandas_saved`.
- `test_get_returns_polars_for_polars_saved`.
- `test_get_as_library_override_polars_to_pandas`.
- `test_get_as_library_override_pandas_to_polars`.
- `test_get_specific_version` — `version=1` on a v2 store returns v1 data.
- `test_get_latest_by_default` — no version arg returns current version data.
- `test_get_nonexistent_raises_df_not_found`.
- `test_get_soft_deleted_raises_df_not_found`.
- `test_get_invalid_version_zero_raises_value_error`.
- `test_get_invalid_version_above_current_raises_value_error`.
- `test_get_roundtrip_data_integrity` — all values and dtypes equal after save/get.

#### `test_list.py`
- `test_list_empty_store_returns_empty_list`.
- `test_list_returns_all_active_records`.
- `test_list_excludes_soft_deleted_by_default`.
- `test_list_include_deleted_returns_soft_deleted`.
- `test_list_sorted_by_updated_at_descending`.

#### `test_info.py`
- `test_info_returns_df_record_with_correct_fields`.
- `test_info_includes_all_version_records`.
- `test_info_nonexistent_raises_df_not_found`.
- `test_info_soft_deleted_still_returns_record`.

#### `test_search.py`
- `test_search_by_description_substring`.
- `test_search_by_description_case_insensitive`.
- `test_search_by_description_no_match_returns_empty`.
- `test_search_by_plain_tag`.
- `test_search_by_dict_tag`.
- `test_search_by_columns_all_must_match`.
- `test_search_by_columns_partial_no_match`.
- `test_search_combined_description_and_tags`.
- `test_search_no_criteria_raises_value_error`.
- `test_search_excludes_soft_deleted`.

#### `test_versions.py`
- `test_versions_single_version_list`.
- `test_versions_multiple_sorted_ascending`.
- `test_versions_nonexistent_raises_df_not_found`.
- `test_versions_shape_diff_correct_after_column_add`.
- `test_versions_shape_diff_none_for_v1`.

#### `test_delete.py`
- `test_soft_delete_sets_deleted_flag_true`.
- `test_soft_delete_hides_from_list`.
- `test_soft_delete_already_deleted_raises_df_store_error`.
- `test_hard_delete_removes_from_index`.
- `test_hard_delete_removes_parquet_directory`.
- `test_hard_delete_not_in_list_include_deleted`.
- `test_restore_after_soft_delete_makes_active`.
- `test_restore_not_deleted_raises_df_store_error`.
- `test_restore_nonexistent_raises_df_not_found`.

#### `test_cli.py` (uses `typer.testing.CliRunner`)
- `test_cli_save_parquet_file_creates_record`.
- `test_cli_list_shows_table_headers`.
- `test_cli_info_shows_description_and_tags`.
- `test_cli_get_stdout_is_valid_csv`.
- `test_cli_search_by_description_returns_match`.
- `test_cli_search_by_tag_returns_match`.
- `test_cli_search_by_column_returns_match`.
- `test_cli_versions_shows_version_rows`.
- `test_cli_delete_soft_sets_deleted`.
- `test_cli_delete_hard_with_confirmation_removes_record`.
- `test_cli_restore_makes_record_active`.
- `test_cli_unknown_name_exits_nonzero`.
- `test_cli_search_no_criteria_exits_nonzero`.

#### `test_metadata.py`
- `test_index_created_on_first_save`.
- `test_index_not_present_before_save`.
- `test_index_is_valid_json_after_save`.
- `test_index_schema_has_required_keys`.
- `test_index_tmp_file_removed_after_write`.

### 10.3 Demo-to-Test Mapping

| Demo step | Primary tests |
|---|---|
| 1. Save pandas | `test_save_pandas_creates_parquet_file`, `test_save_returns_version_record`, `test_save_notes_forced_initial_save_for_v1` |
| 2. Save polars | `test_save_polars_creates_parquet_file` |
| 3. Info | `test_info_returns_df_record_with_correct_fields`, `test_info_includes_all_version_records` |
| 4. Get pandas | `test_get_returns_pandas_for_pandas_saved`, `test_get_roundtrip_data_integrity` |
| 5. Get polars | `test_get_returns_polars_for_polars_saved` |
| 6. Cross-library | `test_get_as_library_override_polars_to_pandas` |
| 7. List | `test_list_returns_all_active_records`, `test_list_sorted_by_updated_at_descending` |
| 8. Versioning | `test_save_increments_version_on_resave`, `test_save_computes_shape_diff_new_column`, `test_save_preserves_description_on_resave` |
| 9. Versions | `test_versions_multiple_sorted_ascending`, `test_versions_shape_diff_correct_after_column_add` |
| 10. Get specific version | `test_get_specific_version` |
| 11. Search by description | `test_search_by_description_substring`, `test_search_by_description_case_insensitive` |
| 12. Search by tags | `test_search_by_plain_tag`, `test_search_by_dict_tag` |
| 13. Search by columns | `test_search_by_columns_all_must_match`, `test_search_by_columns_partial_no_match` |
| 14. Soft delete | `test_soft_delete_sets_deleted_flag_true`, `test_soft_delete_hides_from_list`, `test_search_excludes_soft_deleted`, `test_info_soft_deleted_still_returns_record`, `test_get_soft_deleted_raises_df_not_found` |
| 15. Restore | `test_restore_after_soft_delete_makes_active` |
| 16. Hard delete | `test_hard_delete_removes_from_index`, `test_hard_delete_removes_parquet_directory` |

### 10.4 Coverage Target

≥ 90% line coverage.

```bash
pytest --cov=dfstore --cov-report=term-missing
```

---

## 11. Implementation Order

Implement in this order to avoid circular dependencies:

1. `pyproject.toml` — package metadata, entry point `dfstore = "dfstore.cli:app"`, dependency groups.
2. `src/dfstore/exceptions.py` — no dependencies.
3. `src/dfstore/models.py` — no dependencies.
4. `src/dfstore/storage.py` — depends on models, pyarrow, pandas, polars.
5. `src/dfstore/diff.py` — depends on models only.
6. `src/dfstore/metadata.py` — depends on models, json, os.
7. `src/dfstore/store.py` — depends on metadata, storage, diff, exceptions, models.
8. `src/dfstore/__init__.py` — thin wrappers over `DFStore`; re-exports public API and exceptions.
9. `src/dfstore/cli.py` — depends on store, models, exceptions, rich, typer.
10. `src/dfstore/gui.py` — depends on store, models, exceptions, gradio (optional import).
11. `tests/conftest.py` — fixtures using the public API.
12. All test files — in the order listed in §10.2.

---

## 12. Constraints and Edge Cases

| Constraint | Detail |
|---|---|
| **Name validation** | Regex: `^[a-zA-Z0-9_\-]{1,128}$`. Enforce in every function that accepts `name`. |
| **Thread safety** | `index.json` writes use `os.replace` (atomic on POSIX). No file locking. Concurrent writes from multiple processes may race. Acceptable for solo-user local tool; document in README. |
| **Empty DataFrame** | `save()` must accept zero-row DataFrames. `shape == (0, N)`. `describe == {}`. Not an error. |
| **No numeric columns** | `describe == {}`. Not an error. |
| **`list` builtin shadowing** | The public function is named `list` to match the spec API. Inside `store.py`, use `[]` literals or `builtins.list` when constructing lists to avoid accidental recursion. |
| **Store path auto-creation** | Any API call to a non-existent `store_path` must create it silently. No error raised for a fresh directory. |
| **Missing `index.json`** | `list()` returns `[]`. `get()`/`info()`/`versions()`/`delete()`/`restore()` raise `DFNotFoundError`. Never raise `FileNotFoundError` at the public API boundary. |
| **Polars boolean parquet** | Polars `Boolean` dtype round-trips correctly via parquet. No special handling needed. |
| **Tags format in CLI** | `--tags demo` → plain string. `--tags env=production` → `{'env': 'production'}`. Parser checks for `=` to distinguish the two forms. |
| **`description` on resave** | Passing `description=''` on a re-save preserves the existing description. Passing a non-empty string updates it. |
| **`tags` on resave** | Tags always replace the full list on every save. |
| **Parquet path** | `parquet_file` is stored as a relative path from the store root (e.g. `data/employees/v2.parquet`) so the store directory is relocatable. |
| **Datetime serialization** | All datetimes stored as ISO 8601 UTC strings in `index.json`; deserialized to `datetime` objects with timezone info. |
