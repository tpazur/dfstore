# CLI Reference

dfstore ships with a full command-line interface powered by [Typer](https://typer.tiangolo.com/).

All commands accept `--store-path` to override the default store location.

---

## save

Save a CSV or Parquet file to the store.

```bash
dfstore save <file> --name <name> [options]
```

| Option | Description |
|---|---|
| `--name`, `-n` | DataFrame name (required) |
| `--description`, `-d` | Description |
| `--tags`, `-t` | Tag (repeat for multiple). Use `key=value` for dict tags |
| `--notes` | Version notes |
| `--store-path` | Override store directory |

**Examples:**

```bash
# Save a parquet file
dfstore save data.parquet --name sales_2024 --description "Annual sales"

# Save a CSV with tags
dfstore save data.csv --name employees --tags hr --tags env=production

# Read from stdin
cat data.parquet | dfstore save - --name stream_data
```

---

## get

Retrieve a DataFrame and print it (or write to file).

```bash
dfstore get <name> [options]
```

| Option | Description |
|---|---|
| `--version`, `-v` | Specific version number (default: latest) |
| `--output`, `-o` | Write to file instead of stdout |
| `--format`, `-f` | Output format: `csv` (default), `parquet`, `json` |
| `--store-path` | Override store directory |

**Examples:**

```bash
# Print as CSV
dfstore get sales_2024

# Get a specific version
dfstore get sales_2024 --version 1

# Save to file
dfstore get sales_2024 --output out.parquet --format parquet

# Pipe into another tool
dfstore get sales_2024 --format json | jq '.[0]'
```

---

## list

List all stored DataFrames.

```bash
dfstore list [options]
```

| Option | Description |
|---|---|
| `--include-deleted` | Include soft-deleted entries |
| `--store-path` | Override store directory |

**Example:**

```bash
dfstore list
dfstore list --include-deleted
```

---

## info

Show full metadata for a DataFrame.

```bash
dfstore info <name> [--store-path PATH]
```

Displays description, tags, timestamps, current version, shape, column dtypes, and null counts.

---

## search

Search DataFrames by description, tags, or column names.

```bash
dfstore search [options]
```

| Option | Description |
|---|---|
| `--description`, `-d` | Description substring |
| `--tags`, `-t` | Tag filter (repeat for multiple) |
| `--columns`, `-c` | Column name filter (repeat for multiple) |
| `--store-path` | Override store directory |

**Examples:**

```bash
# Search by description
dfstore search --description "sales"

# Search by tag
dfstore search --tags finance --tags env=production

# Search by column
dfstore search --columns revenue --columns region
```

---

## versions

Show the version history for a DataFrame.

```bash
dfstore versions <name> [--store-path PATH]
```

Displays version number, save timestamp, notes, shape, row diff, and columns added/removed.

---

## delete

Delete a DataFrame.

```bash
dfstore delete <name> [--hard] [--store-path PATH]
```

Without `--hard`, performs a soft delete (hidden but recoverable). With `--hard`, asks for confirmation and permanently removes all data.

---

## restore

Restore a soft-deleted DataFrame.

```bash
dfstore restore <name> [--store-path PATH]
```

---

## serve

Launch the web UI.

```bash
dfstore serve [options]
```

| Option | Description |
|---|---|
| `--port`, `-p` | Port to listen on (default: `7860`) |
| `--host` | Host to bind to (default: `127.0.0.1`) |
| `--store-path` | Override store directory |

```bash
dfstore serve
dfstore serve --port 8080 --host 0.0.0.0
```

Requires `pip install 'dfstore[gui]'`.
