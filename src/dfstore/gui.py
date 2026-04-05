"""dfstore Flask web UI."""
from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

import dfstore
from dfstore.exceptions import DFNotFoundError, DFStoreError
from dfstore.models import DFRecord, VersionRecord


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


def _clean_describe(describe: dict) -> dict:
    """Replace NaN with None so jsonify doesn't choke."""
    return {
        col: {
            stat: None if (isinstance(v, float) and math.isnan(v)) else v
            for stat, v in stats.items()
        }
        for col, stats in describe.items()
    }


def _serialize_version(v: VersionRecord) -> dict:
    return {
        "version": v.version,
        "saved_at": v.saved_at.isoformat(),
        "notes": v.notes,
        "shape": list(v.shape),
        "columns": v.columns,
        "dtypes": v.dtypes,
        "null_counts": v.null_counts,
        "describe": _clean_describe(v.describe),
        "shape_diff": list(v.shape_diff) if v.shape_diff is not None else None,
        "columns_added": v.columns_added,
        "columns_removed": v.columns_removed,
        "row_diff": v.row_diff,
        "library": v.library,
    }


def _serialize_record(r: DFRecord) -> dict:
    return {
        "name": r.name,
        "description": r.description,
        "tags": r.tags,
        "tags_display": _format_tags(r.tags),
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
        "current_version": r.current_version,
        "deleted": r.deleted,
        "versions": [_serialize_version(v) for v in r.versions],
    }


def _api_error(msg: str, status: int = 400):
    return jsonify({"error": msg}), status


def create_app(store_path: Path | None = None) -> Flask:
    try:
        import flask  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Flask is required for the GUI. Install it with: pip install 'dfstore[gui]'"
        ) from exc

    templates_dir = Path(__file__).parent / "templates"
    app = Flask(__name__)

    # ── GET / ─────────────────────────────────────────────────────────────────

    @app.get("/")
    def index():
        return send_from_directory(str(templates_dir), "index.html")

    # ── GET /api/dataframes ───────────────────────────────────────────────────

    @app.get("/api/dataframes")
    def list_dataframes():
        include_deleted = request.args.get("include_deleted", "false").lower() == "true"
        q = request.args.get("q", "").strip().lower()
        try:
            records = dfstore.list(include_deleted=include_deleted, store_path=store_path, format="raw")
        except Exception as e:
            return _api_error(str(e), 500)
        if q:
            records = [r for r in records if q in r.name.lower() or q in r.description.lower()]
        return jsonify([_serialize_record(r) for r in records])

    # ── GET /api/dataframes/<name> ────────────────────────────────────────────

    @app.get("/api/dataframes/<name>")
    def get_dataframe(name: str):
        try:
            r = dfstore.info(name, store_path=store_path, format="raw")
        except DFNotFoundError as e:
            return _api_error(str(e), 404)
        except Exception as e:
            return _api_error(str(e), 500)
        return jsonify(_serialize_record(r))

    # ── GET /api/dataframes/<name>/preview ───────────────────────────────────

    @app.get("/api/dataframes/<name>/preview")
    def preview_dataframe(name: str):
        try:
            n = int(request.args.get("n", 5))
        except ValueError:
            return _api_error("n must be an integer.")
        version_str = request.args.get("version")
        version = int(version_str) if version_str else None
        try:
            data = dfstore.preview(name, n=n, version=version, store_path=store_path)
        except DFNotFoundError as e:
            return _api_error(str(e), 404)
        except Exception as e:
            return _api_error(str(e), 500)
        return jsonify(data)

    # ── POST /api/dataframes ──────────────────────────────────────────────────

    @app.post("/api/dataframes")
    def save_dataframe():
        name = request.form.get("name", "").strip()
        if not name:
            return _api_error("Name is required.")
        if "file" not in request.files or request.files["file"].filename == "":
            return _api_error("A file is required.")

        file = request.files["file"]
        ext = Path(secure_filename(file.filename)).suffix.lower()
        if ext not in (".csv", ".parquet"):
            return _api_error("File must be .csv or .parquet")

        description = request.form.get("description", "")
        tags = _parse_tags(request.form.get("tags", ""))
        notes = request.form.get("notes", "")

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp_path = tmp.name
                file.save(tmp_path)
            df = pd.read_csv(tmp_path) if ext == ".csv" else pd.read_parquet(tmp_path)
        except Exception as e:
            return _api_error(f"Failed to read file: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        try:
            vr = dfstore.save(df, name=name, description=description,
                              tags=tags, notes=notes, store_path=store_path)
        except DFStoreError as e:
            return _api_error(str(e), 409)
        except Exception as e:
            return _api_error(str(e), 500)

        return jsonify({
            "name": name,
            "version": vr.version,
            "shape": list(vr.shape),
            "saved_at": vr.saved_at.isoformat(),
            "message": f"Saved '{name}' version {vr.version} ({vr.shape[0]} rows × {vr.shape[1]} cols)",
        }), 201

    # ── POST /api/dataframes/<name>/delete ────────────────────────────────────

    @app.post("/api/dataframes/<name>/delete")
    def delete_dataframe(name: str):
        body = request.get_json(silent=True) or {}
        hard = bool(body.get("hard", False))
        try:
            dfstore.delete(name, hard=hard, store_path=store_path)
        except DFNotFoundError as e:
            return _api_error(str(e), 404)
        except DFStoreError as e:
            return _api_error(str(e), 400)
        except Exception as e:
            return _api_error(str(e), 500)
        kind = "permanently deleted" if hard else "soft-deleted"
        return jsonify({"message": f"'{name}' has been {kind}."})

    # ── POST /api/dataframes/<name>/restore ───────────────────────────────────

    @app.post("/api/dataframes/<name>/restore")
    def restore_dataframe(name: str):
        try:
            dfstore.restore(name, store_path=store_path)
        except DFNotFoundError as e:
            return _api_error(str(e), 404)
        except DFStoreError as e:
            return _api_error(str(e), 400)
        except Exception as e:
            return _api_error(str(e), 500)
        return jsonify({"message": f"'{name}' has been restored."})

    # ── GET /api/search ───────────────────────────────────────────────────────

    @app.get("/api/search")
    def search_dataframes():
        desc = request.args.get("description", "").strip() or None
        tags_str = request.args.get("tags", "").strip()
        tags = _parse_tags(tags_str) if tags_str else None
        cols_str = request.args.get("columns", "").strip()
        cols = [c.strip() for c in cols_str.split(",") if c.strip()] if cols_str else None

        if desc is None and tags is None and cols is None:
            return _api_error("Provide at least one search criterion.")

        try:
            results = dfstore.search(
                description=desc, tags=tags, columns=cols,
                store_path=store_path, format="raw",
            )
        except Exception as e:
            return _api_error(str(e), 500)

        return jsonify([_serialize_record(r) for r in results])

    return app
