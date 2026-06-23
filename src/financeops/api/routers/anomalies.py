"""Anomaly endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from financeops.anomaly.detector import detect_all
from financeops.api.schemas import AnomalyOut

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=list[AnomalyOut])
def list_anomalies(
    severity: str | None = Query(None, pattern="^(low|medium|high)$"),
    limit: int = Query(50, ge=1, le=500),
):
    items = detect_all()
    if severity:
        items = [a for a in items if a["severity"] == severity]
    return items[:limit]