"""CSV export utilities."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from financeops.anomaly.detector import detect_all
from financeops.config import get_settings
from financeops.kpi.engine import region_performance, revenue_trend

settings = get_settings()


def export_csv_bundle(out_dir: Path | None = None) -> dict[str, str]:
    out_dir = out_dir or settings.reports_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.date.today().isoformat()

    paths = {}
    files = {
        "daily_trend": revenue_trend("D"),
        "weekly_trend": revenue_trend("W"),
        "region_performance": region_performance(),
        "anomalies": pd.DataFrame(detect_all()),
    }
    for name, df in files.items():
        p = out_dir / f"{name}_{stamp}.csv"
        df.to_csv(p, index=False)
        paths[name] = str(p)
    return paths