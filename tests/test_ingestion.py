"""Tests for the ingestion and validation layer."""
from __future__ import annotations

import pandas as pd

from financeops.ingestion.validators import ORDERS_SCHEMA, validate
from financeops.ingestion.quality import profile


def test_validate_rejects_bad_rows():
    df = pd.DataFrame({
        "order_id": ["A", "B", "C"],
        "order_date": ["2024-01-01", "2024-01-02", "bad-date"],
        "customer_id": ["c1", None, "c3"],          # row B missing key
        "product_id": ["p1", "p2", "p3"],
        "region_id": ["r1", "r2", "r3"],
        "quantity": [1, 2, 0],                       # row C below min
        "gross_revenue": [100.0, -5.0, 50.0],        # row B negative
        "cost": [60.0, 40.0, 30.0],
    })
    clean, rejected = validate(df, ORDERS_SCHEMA)
    assert len(clean) == 1
    assert len(rejected) == 2
    assert "_reject_reason" in rejected.columns


def test_validate_missing_required_column_raises():
    df = pd.DataFrame({"order_id": ["A"]})
    try:
        validate(df, ORDERS_SCHEMA)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "missing required columns" in str(exc)


def test_quality_profile_flags_completeness():
    df = pd.DataFrame({
        "order_id": ["a", "b"], "order_date": ["2024-01-01", "2024-01-02"],
        "gross_revenue": [10.0, 20.0],
    })
    report = profile(df, "orders", "order_date")
    assert report.row_count == 2
    assert report.completeness["order_id"] == 100.0