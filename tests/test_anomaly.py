"""Tests for the anomaly detector."""
from __future__ import annotations

from financeops.anomaly.detector import detect_all


def test_detects_some_anomalies():
    anomalies = detect_all()
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0


def test_direction_matches_deviation_sign():
    for a in detect_all():
        if a["direction"] == "drop":
            assert a["deviation_pct"] < 0, a
        else:
            assert a["deviation_pct"] > 0, a


def test_severity_values_valid():
    for a in detect_all():
        assert a["severity"] in {"low", "medium", "high"}
        assert a["method"] in {"zscore", "pct_change"}