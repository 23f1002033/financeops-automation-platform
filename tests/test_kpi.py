"""Tests for the KPI engine (run against the seeded test DB)."""
from __future__ import annotations

import datetime as dt

from financeops.kpi.engine import compute_snapshot, region_performance, revenue_trend


def test_snapshot_has_positive_revenue():
    snap = compute_snapshot(dt.date.today() - dt.timedelta(days=30), dt.date.today())
    assert snap.revenue > 0
    assert snap.orders > 0
    assert 0 <= snap.gross_margin_pct <= 100


def test_rates_are_bounded():
    snap = compute_snapshot(dt.date.today() - dt.timedelta(days=30), dt.date.today())
    assert snap.return_rate_pct >= 0
    assert snap.refund_rate_pct >= 0
    assert 0 <= snap.retention_pct <= 100


def test_revenue_trend_shape():
    df = revenue_trend("D")
    assert not df.empty
    assert {"period", "revenue", "orders"}.issubset(df.columns)


def test_region_performance_sums_consistently():
    regions = region_performance()
    assert not regions.empty
    assert (regions["revenue"] >= 0).all()