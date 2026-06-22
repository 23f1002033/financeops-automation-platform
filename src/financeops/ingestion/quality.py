"""Data-quality profiling: completeness, duplicates, freshness."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd


@dataclass
class QualityReport:
    dataset: str
    row_count: int
    duplicate_rows: int
    completeness: dict[str, float]   # column -> % non-null
    freshness_days: float | None     # days since most recent date
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def profile(df: pd.DataFrame, dataset: str, date_col: str | None = None) -> QualityReport:
    row_count = len(df)
    dupes = int(df.duplicated().sum())

    completeness = {
        col: round(float(df[col].notna().mean() * 100), 2) for col in df.columns
    }

    freshness = None
    if date_col and date_col in df.columns and row_count:
        latest = pd.to_datetime(df[date_col], errors="coerce").max()
        if pd.notna(latest):
            freshness = round((pd.Timestamp.now().normalize() - latest.normalize()).days, 1)

    key_complete = all(
        completeness.get(c, 0) > 95
        for c in df.columns
        if c.endswith("_id") or c.endswith("_date")
    )
    passed = bool(
        row_count > 0
        and (dupes / row_count if row_count else 0) < 0.05
        and key_complete
    )

    return QualityReport(
        dataset=dataset,
        row_count=row_count,
        duplicate_rows=dupes,
        completeness=completeness,
        freshness_days=freshness,
        passed=passed,
    )