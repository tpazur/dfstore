"""Parquet read/write for pandas and polars DataFrames."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import polars as pl


def write_parquet(df: pd.DataFrame | pl.DataFrame, path: Path) -> None:
    """Write *df* to *path* as a Parquet file, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(df, pd.DataFrame):
        df.to_parquet(path, index=False)
    elif isinstance(df, pl.DataFrame):
        df.write_parquet(path)
    else:
        raise TypeError(f"Expected pd.DataFrame or pl.DataFrame, got {type(df).__name__}")


def read_parquet(path: Path, library: str) -> pd.DataFrame | pl.DataFrame:
    """Read a Parquet file and return a DataFrame in the requested *library*."""
    if library == "pandas":
        return pd.read_parquet(path)
    elif library == "polars":
        return pl.read_parquet(path)
    else:
        raise ValueError(f"Unknown library: {library!r}")


def compute_metadata(df: pd.DataFrame | pl.DataFrame) -> dict:
    """Extract shape, columns, dtypes, null_counts, and describe from a DataFrame."""
    if isinstance(df, pd.DataFrame):
        return _metadata_pandas(df)
    elif isinstance(df, pl.DataFrame):
        return _metadata_polars(df)
    else:
        raise TypeError(f"Expected pd.DataFrame or pl.DataFrame, got {type(df).__name__}")


def _metadata_pandas(df: pd.DataFrame) -> dict:
    """Extract shape, columns, dtypes, null counts, and describe stats from a pandas DataFrame."""
    shape = tuple(df.shape)
    columns = list(df.columns)
    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    null_counts = {col: int(df[col].isna().sum()) for col in columns}

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    describe: dict[str, dict[str, float]] = {}
    if numeric_cols:
        desc = df[numeric_cols].describe()
        for col in numeric_cols:
            describe[col] = {k: float(v) for k, v in desc[col].items()}

    return {
        "shape": shape,
        "columns": columns,
        "dtypes": dtypes,
        "null_counts": null_counts,
        "describe": describe,
    }


def _metadata_polars(df: pl.DataFrame) -> dict:
    """Extract shape, columns, dtypes, null counts, and describe stats from a polars DataFrame."""
    shape = tuple(df.shape)
    columns = list(df.columns)
    dtypes = {col: str(dtype) for col, dtype in zip(df.columns, df.dtypes)}
    null_counts = {col: int(df[col].null_count()) for col in columns}

    numeric_types = (
        pl.Int8, pl.Int16, pl.Int32, pl.Int64,
        pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
        pl.Float32, pl.Float64,
    )
    numeric_cols = [
        col for col, dtype in zip(df.columns, df.dtypes)
        if isinstance(dtype, numeric_types)
    ]
    describe: dict[str, dict[str, float]] = {}
    if numeric_cols:
        desc = df.select(numeric_cols).describe()
        stat_col = desc.columns[0]
        stats = desc[stat_col].to_list()
        for col in numeric_cols:
            values = desc[col].to_list()
            describe[col] = {stat: float(val) if val is not None else 0.0
                             for stat, val in zip(stats, values)}

    return {
        "shape": shape,
        "columns": columns,
        "dtypes": dtypes,
        "null_counts": null_counts,
        "describe": describe,
    }
