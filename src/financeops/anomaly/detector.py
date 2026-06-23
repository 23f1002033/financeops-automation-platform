"""Anomaly detection — rolling z-score + day-over-day, all explainable."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import pandas as pd

from financeops.config import get_settings
from financeops.kpi.engine import load_returns, revenue_trend
from financeops.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class Anomaly:
    metric: str
    date: str
    value: float
    expected: float
    deviation_pct: float
    direction: str        # "drop" | "spike"
    severity: str         # "low" | "medium" | "high"
    method: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _severity(dev_pct: float) -> str:
    a = abs(dev_pct)
    if a >= 40:
        return "high"
    if a >= 25:
        return "medium"
    return "low"


def _scan_series(s: pd.Series, metric: str, watch: str, min_material_dev: float = 8.0) -> list[Anomaly]:
    """Run both detectors over a date-indexed numeric series."""
    out: list[Anomaly] = []
    if len(s) < settings.anomaly_rolling_window + 1:
        return out

    window = settings.anomaly_rolling_window
    roll_mean = s.shift(1).rolling(window).mean()
    roll_std = s.shift(1).rolling(window).std(ddof=0)
    z = (s - roll_mean) / roll_std.replace(0, pd.NA)
    pct = s.pct_change()

    for date, val in s.items():
        expected = roll_mean.get(date)
        if pd.isna(expected) or expected == 0:
            continue
        dev_pct = (val - expected) / expected * 100
        if abs(dev_pct) < min_material_dev:
            continue
        zval = z.get(date)
        pctval = pct.get(date)

        z_hit = pd.notna(zval) and abs(zval) >= settings.anomaly_zscore_threshold
        pct_hit = pd.notna(pctval) and abs(pctval) >= settings.anomaly_pct_drop_threshold
        if not (z_hit or pct_hit):
            continue

        direction = "drop" if dev_pct < 0 else "spike"
        if watch not in (direction, "both"):
            continue

        method = "zscore" if z_hit else "pct_change"
        verb = "fell to" if direction == "drop" else "spiked to"
        prep = "below" if direction == "drop" else "above"
        out.append(Anomaly(
            metric=metric, date=str(pd.Timestamp(date).date()),
            value=round(float(val), 2), expected=round(float(expected), 2),
            deviation_pct=round(float(dev_pct), 1), direction=direction,
            severity=_severity(dev_pct), method=method,
            message=(f"{metric} {verb} {val:,.0f}, {abs(dev_pct):.0f}% {prep} the "
                     f"{window}-day expected {expected:,.0f}."),
        ))
    return out

def detect_all() -> list[dict]:
    """Run the full anomaly suite across revenue, orders, and refunds."""
    anomalies: list[Anomaly] = []

    trend = revenue_trend("D")
    if not trend.empty:
        trend = trend.set_index("period")
        anomalies += _scan_series(trend["revenue"], "daily_revenue", watch="drop")
        anomalies += _scan_series(trend["orders"].astype(float), "daily_orders", watch="drop")

    returns = load_returns()
    if not returns.empty:
        daily_refunds = (
            returns.set_index("return_date")
            .groupby(pd.Grouper(freq="D"))["refund_amount"]
            .sum()
            .asfreq("D", fill_value=0.0)
        )
        # Daily refunds low-volume pe spiky hote hain, isliye 7-day rolling sum pe detect
        smoothed = daily_refunds.rolling(7, min_periods=7).sum().dropna()
        anomalies += _scan_series(smoothed, "refunds_7d", watch="spike", min_material_dev=25.0)

    anomalies.sort(key=lambda a: (a.date, a.severity), reverse=True)
    logger.info("Detected %d anomalies", len(anomalies))
    return [a.to_dict() for a in anomalies]