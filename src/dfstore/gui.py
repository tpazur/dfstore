"""dfstore Gradio web UI."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

import dfstore
from dfstore.exceptions import DFNotFoundError, DFStoreError


def _format_tags(tags: list) -> str:
    parts = []
    for t in tags:
        if isinstance(t, dict):
            parts.extend(f"{k}={v}" for k, v in t.items())
        else:
            parts.append(str(t))
    return ", ".join(parts)


def _parse_tags(tags_str: str) -> list:
    tags = []
    for part in tags_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, _, v = part.partition("=")
            tags.append({k.strip(): v.strip()})
        else:
            tags.append(part)
    return tags


def _records_to_table(records):
    rows = []
    for r in records:
        vr = r.versions[r.current_version - 1]
        rows.append({
            "Name": r.name,
            "Description": r.description,
            "Tags": _format_tags(r.tags),
            "Last Updated": r.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Version": r.current_version,
            "Shape": f"({vr.shape[0]}, {vr.shape[1]})",
            "Deleted": "Yes" if r.deleted else "No",
        })
    return rows


def create_app(store_path: Path | None = None):
    try:
        import gradio as gr
    except ImportError as exc:
        raise ImportError(
            "Gradio is required for the GUI. Install it with: pip install 'dfstore[gui]'"
        ) from exc

    # ── Tab 1: Browse ─────────────────────────────────────────────────────────

    def browse_refresh(search_text: str, include_deleted: bool):
        try:
            records = dfstore.list(include_deleted=include_deleted, store_path=store_path)
            if search_text:
                q = search_text.lower()
                records = [r for r in records if q in r.name.lower() or q in r.description.lower()]
            rows = _records_to_table(records)
            names = [r["Name"] for r in rows]
            return rows, gr.Dropdown(choices=names, value=names[0] if names else None)
        except Exception as e:
            return [], gr.Dropdown(choices=[])

    def browse_info(name: str):
        if not name:
            return ""
        try:
            r = dfstore.info(name, store_path=store_path)
            vr = r.versions[r.current_version - 1]
            return (
                f"Name: {r.name}\n"
                f"Description: {r.description}\n"
                f"Tags: {_format_tags(r.tags)}\n"
                f"Created: {r.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Updated: {r.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Version: {r.current_version}\n"
                f"Shape: ({vr.shape[0]}, {vr.shape[1]})\n"
                f"Deleted: {'Yes' if r.deleted else 'No'}\n"
                f"Columns: {', '.join(vr.columns)}"
            )
        except DFNotFoundError:
            return f"'{name}' not found."

    def browse_versions(name: str):
        if not name:
            return gr.Dropdown(choices=[])
        try:
            vrs = dfstore.versions(name, store_path=store_path)
            choices = [str(v.version) for v in vrs]
            return gr.Dropdown(choices=choices, value=choices[-1] if choices else None)
        except DFNotFoundError:
            return gr.Dropdown(choices=[])

    def browse_load(name: str, version_str: str):
        if not name:
            return None, "Select a DataFrame first."
        try:
            version = int(version_str) if version_str else None
            df = dfstore.get(name, version=version, as_library="pandas", store_path=store_path)
            return df.head(100), f"Showing first {min(100, len(df))} of {len(df)} rows."
        except (DFNotFoundError, ValueError) as e:
            return None, str(e)

    # ── Tab 2: Save ───────────────────────────────────────────────────────────

    def do_save(file, name: str, description: str, tags_str: str, notes: str):
        if not name:
            return "Error: Name is required."
        if file is None:
            return "Error: Please upload a file."
        try:
            file_path = Path(file.name)
            if file_path.suffix.lower() == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_parquet(file_path)
            tags = _parse_tags(tags_str)
            vr = dfstore.save(df, name=name, description=description,
                              tags=tags, notes=notes, store_path=store_path)
            return f"Saved '{name}' version {vr.version} ({vr.shape[0]} rows × {vr.shape[1]} cols)"
        except Exception as e:
            return f"Error: {e}"

    # ── Tab 3: Search ─────────────────────────────────────────────────────────

    def do_search(desc: str, tags_str: str, cols_str: str):
        desc = desc.strip() or None
        tags = _parse_tags(tags_str) or None
        cols = [c.strip() for c in cols_str.split(",") if c.strip()] or None
        if desc is None and tags is None and cols is None:
            return [], "Provide at least one search criterion."
        try:
            results = dfstore.search(description=desc, tags=tags, columns=cols,
                                     store_path=store_path)
            return _records_to_table(results), f"{len(results)} result(s) found."
        except Exception as e:
            return [], str(e)

    # ── Tab 4: Manage ─────────────────────────────────────────────────────────

    def manage_load_names():
        try:
            records = dfstore.list(include_deleted=True, store_path=store_path)
            names = [r.name for r in records]
            return gr.Dropdown(choices=names, value=names[0] if names else None)
        except Exception:
            return gr.Dropdown(choices=[])

    def do_soft_delete(name: str, confirmed: bool):
        if not confirmed:
            return "Check the confirmation box first."
        try:
            dfstore.delete(name, hard=False, store_path=store_path)
            return f"'{name}' has been soft-deleted."
        except (DFNotFoundError, DFStoreError) as e:
            return str(e)

    def do_hard_delete(name: str, confirmed: bool):
        if not confirmed:
            return "Check the confirmation box first."
        try:
            dfstore.delete(name, hard=True, store_path=store_path)
            return f"'{name}' has been permanently deleted."
        except (DFNotFoundError, DFStoreError) as e:
            return str(e)

    def do_restore(name: str):
        try:
            dfstore.restore(name, store_path=store_path)
            return f"'{name}' has been restored."
        except (DFNotFoundError, DFStoreError) as e:
            return str(e)

    # ── Build UI ──────────────────────────────────────────────────────────────

    with gr.Blocks(title="dfstore") as demo:
        gr.Markdown("# dfstore — DataFrame Storage")

        with gr.Tab("Browse"):
            with gr.Row():
                browse_search = gr.Textbox(label="Search (name or description)", scale=3)
                browse_deleted = gr.Checkbox(label="Include deleted", scale=1)
                browse_btn = gr.Button("Refresh", scale=1)
            browse_table = gr.Dataframe(label="DataFrames", interactive=False)
            browse_name_dd = gr.Dropdown(label="Selected DataFrame", choices=[])
            browse_info_box = gr.Textbox(label="Info", lines=10, interactive=False)
            browse_ver_dd = gr.Dropdown(label="Version", choices=[])
            browse_load_btn = gr.Button("Load Data")
            browse_status = gr.Textbox(label="", interactive=False)
            browse_preview = gr.Dataframe(label="Preview (first 100 rows)", interactive=False)

            browse_btn.click(browse_refresh, [browse_search, browse_deleted],
                             [browse_table, browse_name_dd])
            browse_search.change(browse_refresh, [browse_search, browse_deleted],
                                 [browse_table, browse_name_dd])
            browse_name_dd.change(browse_info, [browse_name_dd], [browse_info_box])
            browse_name_dd.change(browse_versions, [browse_name_dd], [browse_ver_dd])
            browse_load_btn.click(browse_load, [browse_name_dd, browse_ver_dd],
                                  [browse_preview, browse_status])

        with gr.Tab("Save"):
            save_file = gr.File(label="Upload file (.parquet or .csv)")
            save_name = gr.Textbox(label="Name (required)")
            save_desc = gr.Textbox(label="Description")
            save_tags = gr.Textbox(label="Tags (comma-separated; use key=value for dict tags)")
            save_notes = gr.Textbox(label="Notes")
            save_btn = gr.Button("Save", variant="primary")
            save_status = gr.Textbox(label="Status", interactive=False)

            save_btn.click(do_save, [save_file, save_name, save_desc, save_tags, save_notes],
                           [save_status])

        with gr.Tab("Search"):
            s_desc = gr.Textbox(label="Description contains")
            s_tags = gr.Textbox(label="Tags (comma-separated)")
            s_cols = gr.Textbox(label="Columns (comma-separated)")
            s_btn = gr.Button("Search", variant="primary")
            s_status = gr.Textbox(label="Status", interactive=False)
            s_table = gr.Dataframe(label="Results", interactive=False)

            s_btn.click(do_search, [s_desc, s_tags, s_cols], [s_table, s_status])

        with gr.Tab("Manage"):
            m_refresh_btn = gr.Button("Refresh list")
            m_name_dd = gr.Dropdown(label="Select DataFrame", choices=[])

            with gr.Row():
                m_soft_confirm = gr.Checkbox(label="I understand this will hide the DataFrame")
                m_soft_btn = gr.Button("Soft Delete")
            with gr.Row():
                m_hard_confirm = gr.Checkbox(label="I understand this is permanent and irreversible")
                m_hard_btn = gr.Button("Hard Delete", variant="stop")
            m_restore_btn = gr.Button("Restore")
            m_status = gr.Textbox(label="Status", interactive=False)

            m_refresh_btn.click(manage_load_names, [], [m_name_dd])
            m_soft_btn.click(do_soft_delete, [m_name_dd, m_soft_confirm], [m_status])
            m_hard_btn.click(do_hard_delete, [m_name_dd, m_hard_confirm], [m_status])
            m_restore_btn.click(do_restore, [m_name_dd], [m_status])

    return demo
