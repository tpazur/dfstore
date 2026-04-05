"""dfstore CLI — Typer + Rich."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Annotated, Optional

import pandas as pd
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import dfstore
from dfstore.exceptions import DFNotFoundError, DFStoreError

app = typer.Typer(help="dfstore — centralized DataFrame storage.", no_args_is_help=True)
console = Console()
err_console = Console(stderr=True, style="red")

_STORE_OPT = typer.Option("--store-path", help="Override store directory.")


def _tags_from_strings(tag_strings: list[str]) -> list:
    tags = []
    for t in tag_strings:
        if "=" in t:
            k, _, v = t.partition("=")
            tags.append({k: v})
        else:
            tags.append(t)
    return tags


def _format_tags(tags: list) -> str:
    parts = []
    for t in tags:
        if isinstance(t, dict):
            parts.extend(f"{k}={v}" for k, v in t.items())
        else:
            parts.append(str(t))
    return ", ".join(parts)


def _records_table(records: list, title: str = "") -> Table:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Tags")
    table.add_column("Last Updated")
    table.add_column("Version", justify="right")
    table.add_column("Shape")
    for r in records:
        vr = r.versions[r.current_version - 1]
        table.add_row(
            r.name,
            r.description,
            _format_tags(r.tags),
            r.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            str(r.current_version),
            f"({vr.shape[0]}, {vr.shape[1]})",
        )
    return table


# ── save ──────────────────────────────────────────────────────────────────────

@app.command()
def save(
    file: Annotated[Path, typer.Argument(help="Parquet or CSV file to save. Use '-' for stdin parquet.")],
    name: Annotated[str, typer.Option("--name", "-n", help="DataFrame name (required).")],
    description: Annotated[str, typer.Option("--description", "-d", help="Description.")] = "",
    tags: Annotated[Optional[list[str]], typer.Option("--tags", "-t", help="Tag (repeat for multiple). Use key=value for dict tags.")] = None,
    notes: Annotated[str, typer.Option("--notes", help="Version notes.")] = "",
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Save a parquet or CSV file to the store."""
    try:
        if str(file) == "-":
            df = pd.read_parquet(io.BytesIO(sys.stdin.buffer.read()))
        elif file.suffix.lower() == ".csv":
            df = pd.read_csv(file)
        else:
            df = pd.read_parquet(file)

        tag_list = _tags_from_strings(tags or [])
        vr = dfstore.save(df, name=name, description=description, tags=tag_list,
                          notes=notes, store_path=store_path)
        console.print(f"Saved [bold]{name!r}[/bold] version {vr.version} "
                      f"({vr.shape[0]} rows × {vr.shape[1]} cols)")
    except (DFNotFoundError, DFStoreError, ValueError, TypeError) as e:
        err_console.print(str(e))
        raise typer.Exit(1)


# ── get ───────────────────────────────────────────────────────────────────────

@app.command()
def get(
    name: Annotated[str, typer.Argument(help="DataFrame name.")],
    version: Annotated[Optional[int], typer.Option("--version", "-v", help="Specific version.")] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output file path.")] = None,
    fmt: Annotated[str, typer.Option("--format", "-f", help="Output format: csv, parquet, json.")] = "csv",
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Retrieve a DataFrame from the store."""
    try:
        df = dfstore.get(name, version=version, as_library="pandas", store_path=store_path)
    except (DFNotFoundError, ValueError) as e:
        err_console.print(str(e))
        raise typer.Exit(1)

    if output:
        if fmt == "parquet":
            df.to_parquet(output, index=False)
        elif fmt == "json":
            df.to_json(output, orient="records", indent=2)
        else:
            df.to_csv(output, index=False)
        console.print(f"Written to {output}")
    else:
        if fmt == "parquet":
            sys.stdout.buffer.write(df.to_parquet(index=False))
        elif fmt == "json":
            console.print(df.to_json(orient="records", indent=2))
        else:
            console.print(df.to_csv(index=False), end="")


# ── list ──────────────────────────────────────────────────────────────────────

@app.command(name="list")
def list_cmd(
    include_deleted: Annotated[bool, typer.Option("--include-deleted", help="Include soft-deleted items.")] = False,
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """List all stored DataFrames."""
    records = dfstore.list(include_deleted=include_deleted, store_path=store_path, format="raw")
    if not records:
        console.print("No DataFrames stored yet.")
        return
    console.print(_records_table(records))


# ── info ──────────────────────────────────────────────────────────────────────

@app.command()
def info(
    name: Annotated[str, typer.Argument(help="DataFrame name.")],
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Show full metadata for a DataFrame."""
    try:
        r = dfstore.info(name, store_path=store_path, format="raw")
    except DFNotFoundError as e:
        err_console.print(str(e))
        raise typer.Exit(1)

    vr = r.versions[r.current_version - 1]

    dtypes_str = "\n".join(f"  {col:30s} {dtype}" for col, dtype in vr.dtypes.items())
    null_str = "  " + "  ".join(f"{col}: {n}" for col, n in vr.null_counts.items())

    content = (
        f"Description : {r.description}\n"
        f"Tags        : {_format_tags(r.tags)}\n"
        f"Created     : {r.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Updated     : {r.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Version     : {r.current_version}\n"
        f"Shape       : ({vr.shape[0]}, {vr.shape[1]})\n"
        f"Deleted     : {'Yes' if r.deleted else 'No'}\n"
        f"\nColumns & Dtypes (current version)\n{dtypes_str}\n"
        f"\nNull Counts\n{null_str}"
    )
    console.print(Panel(content, title=f"[bold]{name}[/bold]"))


# ── search ────────────────────────────────────────────────────────────────────

@app.command()
def search(
    description: Annotated[Optional[str], typer.Option("--description", "-d", help="Description substring.")] = None,
    tags: Annotated[Optional[list[str]], typer.Option("--tags", "-t", help="Tag filter (repeat for multiple).")] = None,
    columns: Annotated[Optional[list[str]], typer.Option("--columns", "-c", help="Column name filter (repeat for multiple).")] = None,
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Search DataFrames by description, tags, or columns."""
    if description is None and not tags and not columns:
        err_console.print("Provide at least one of --description, --tags, or --columns.")
        raise typer.Exit(1)

    try:
        tag_list = _tags_from_strings(tags or []) or None
        results = dfstore.search(
            description=description,
            tags=tag_list,
            columns=columns or None,
            store_path=store_path,
            format="raw",
        )
    except ValueError as e:
        err_console.print(str(e))
        raise typer.Exit(1)

    if not results:
        console.print("No results found.")
        return
    console.print(_records_table(results, title="Search Results"))


# ── versions ──────────────────────────────────────────────────────────────────

@app.command()
def versions(
    name: Annotated[str, typer.Argument(help="DataFrame name.")],
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Show version history for a DataFrame."""
    try:
        vrs = dfstore.versions(name, store_path=store_path, format="raw")
    except DFNotFoundError as e:
        err_console.print(str(e))
        raise typer.Exit(1)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Version", justify="right")
    table.add_column("Saved At")
    table.add_column("Notes")
    table.add_column("Shape")
    table.add_column("Row Diff", justify="right")
    table.add_column("Cols Added")
    table.add_column("Cols Removed")

    for v in vrs:
        table.add_row(
            str(v.version),
            v.saved_at.strftime("%Y-%m-%d %H:%M:%S"),
            v.notes,
            f"({v.shape[0]}, {v.shape[1]})",
            "—" if v.shape_diff is None else str(v.row_diff),
            "—" if not v.columns_added else ", ".join(v.columns_added),
            "—" if not v.columns_removed else ", ".join(v.columns_removed),
        )
    console.print(table)


# ── delete ────────────────────────────────────────────────────────────────────

@app.command()
def delete(
    name: Annotated[str, typer.Argument(help="DataFrame name.")],
    hard: Annotated[bool, typer.Option("--hard", help="Permanently delete data and metadata.")] = False,
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Delete a DataFrame (soft by default)."""
    try:
        if hard:
            confirmed = typer.confirm(
                f"Are you sure you want to permanently delete '{name}' and all its versions?"
            )
            if not confirmed:
                console.print("Aborted.")
                raise typer.Exit(0)
        dfstore.delete(name, hard=hard, store_path=store_path)
        if hard:
            console.print(f"[bold]{name!r}[/bold] has been permanently deleted.")
        else:
            console.print(
                f"[bold]{name!r}[/bold] has been soft-deleted. "
                f"Use 'dfstore restore {name}' to recover it."
            )
    except (DFNotFoundError, DFStoreError) as e:
        err_console.print(str(e))
        raise typer.Exit(1)


# ── restore ───────────────────────────────────────────────────────────────────

@app.command()
def restore(
    name: Annotated[str, typer.Argument(help="DataFrame name.")],
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Restore a soft-deleted DataFrame."""
    try:
        dfstore.restore(name, store_path=store_path)
        console.print(f"[bold]{name!r}[/bold] has been restored.")
    except (DFNotFoundError, DFStoreError) as e:
        err_console.print(str(e))
        raise typer.Exit(1)


# ── serve ─────────────────────────────────────────────────────────────────────

@app.command()
def serve(
    port: Annotated[int, typer.Option("--port", "-p", help="Port to listen on.")] = 7860,
    host: Annotated[str, typer.Option("--host", help="Host to bind to.")] = "127.0.0.1",
    store_path: Annotated[Optional[Path], _STORE_OPT] = None,
) -> None:
    """Launch the dfstore web UI."""
    try:
        from dfstore.gui import create_app
    except ImportError:
        err_console.print(
            "GUI dependencies not installed. Run: pip install 'dfstore[gui]'"
        )
        raise typer.Exit(1)

    console.print(f"dfstore UI running at http://{host}:{port}")
    resolved = store_path or Path(os.environ.get("DFSTORE_PATH", Path.home() / ".dfstore"))
    flask_app = create_app(store_path=resolved)
    flask_app.run(host=host, port=port, debug=False)
