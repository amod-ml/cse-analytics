from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def _json_files(dir_path: Path) -> Iterable[Path]:
    """Yield every *.json file directly inside *dir_path*."""
    return dir_path.glob("*.json")


def _infer_date_from_stem(stem: str) -> str:  # helper for robustness
    try:
        d, m, y = stem.split("_")
        return f"{y}-{m}-{d}"
    except ValueError:
        return stem


def merge_quarterly_files(dir_path: Path) -> pd.DataFrame:
    """
    Read & merge all JSON files in *dir_path* into a tidy, sorted DataFrame.
    """
    records: list[dict] = []
    for fp in _json_files(dir_path):
        with fp.open(encoding="utf-8") as f:
            rec = json.load(f)
        rec.setdefault("period_end_date", _infer_date_from_stem(fp.stem))
        records.append(rec)

    quarterly_df = pd.DataFrame.from_records(records)

    # tidy
    quarterly_df["period_end_date"] = pd.to_datetime(quarterly_df["period_end_date"], errors="coerce")
    numeric_cols = [
        "revenue",
        "cost_of_sales",
        "gross_profit",
        "operating_expenses",
        "profit_before_tax",
        "net_income_parent",
    ]
    quarterly_df[numeric_cols] = quarterly_df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    quarterly_df = quarterly_df.sort_values("period_end_date").reset_index(drop=True)
    return quarterly_df


def save_outputs(quarterly_df: pd.DataFrame, out_dir: Path) -> dict[str, str]:
    """
    Save *quarterly_df* as both CSV and Parquet inside *out_dir*.
    Returns a mapping of {'csv': path, 'parquet': path}.
    """
    csv_path = out_dir / "rpe_quarterlies.csv"
    parquet_path = out_dir / "rpe_quarterlies.parquet"
    quarterly_df.to_csv(csv_path, index=False)
    quarterly_df.to_parquet(parquet_path, index=False)
    return {"csv": str(csv_path), "parquet": str(parquet_path)}
