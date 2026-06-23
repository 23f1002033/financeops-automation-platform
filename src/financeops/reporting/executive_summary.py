"""Executive summary builder — deterministic, rule-based (no LLM, fully auditable)."""
from __future__ import annotations

import datetime as dt

from financeops.anomaly.detector import detect_all
from financeops.kpi.engine import compute_snapshot, region_performance


def build_summary(start: dt.date | None = None, end: dt.date | None = None) -> dict:
    snap = compute_snapshot(start, end)
    anomalies = detect_all()
    regions = region_performance()

    headline = (
        f"Revenue of Rs {snap.revenue:,.0f} across {snap.orders:,} orders "
        f"at {snap.gross_margin_pct:.1f}% gross margin."
    )
    growth_note = (
        f"Order volume {'up' if snap.order_growth_pct >= 0 else 'down'} "
        f"{abs(snap.order_growth_pct):.1f}% vs the prior comparable window."
    )

    risk_lines = []
    if snap.refund_rate_pct > 5:
        risk_lines.append(f"Refund rate elevated at {snap.refund_rate_pct:.1f}% of revenue.")
    if snap.return_rate_pct > 10:
        risk_lines.append(f"Return rate high at {snap.return_rate_pct:.1f}% of orders.")
    high_sev = [a for a in anomalies if a["severity"] == "high"]
    if high_sev:
        risk_lines.append(f"{len(high_sev)} high-severity anomalies need review.")

    top_region = regions.iloc[0]["zone"] if not regions.empty else "n/a"

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "period": {"start": snap.period_start, "end": snap.period_end},
        "headline": headline,
        "growth": growth_note,
        "top_region": top_region,
        "retention_pct": round(snap.retention_pct, 1),
        "risks": risk_lines or ["No material finance risks flagged this period."],
        "kpis": snap.to_dict(),
        "anomaly_count": len(anomalies),
        "anomalies_top": anomalies[:5],
    }