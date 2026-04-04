"""Compute shape and column diffs between two VersionRecords."""
from __future__ import annotations

from .models import VersionRecord


def compute_diff(prev: VersionRecord, curr_meta: dict) -> dict:
    """
    Given the previous VersionRecord and current version metadata dict,
    return diff fields: shape_diff, columns_added, columns_removed, row_diff.
    """
    prev_rows, prev_cols = prev.shape
    curr_rows, curr_cols = curr_meta["shape"]

    row_diff = curr_rows - prev_rows
    col_diff = curr_cols - prev_cols
    shape_diff = (row_diff, col_diff)

    prev_col_set = set(prev.columns)
    curr_col_set = set(curr_meta["columns"])

    columns_added = [c for c in curr_meta["columns"] if c not in prev_col_set]
    columns_removed = [c for c in prev.columns if c not in curr_col_set]

    return {
        "shape_diff": shape_diff,
        "columns_added": columns_added,
        "columns_removed": columns_removed,
        "row_diff": row_diff,
    }
