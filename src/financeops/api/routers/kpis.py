"""KPI endpoints."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query

from financeops.api.schemas import KpiSnapshotResponse, RegionRow, TrendPoint
from financeops.kpi.engine import (
    category_performance, compute_snapshot, region_performance, revenue_trend,
)

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("/snapshot", response_model=KpiSnapshotResponse)
def snapshot(days: int = Query(30, ge=1, le=365, description="Look-back window in days")):
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    return compute_snapshot(start, end).to_dict()


@router.get("/trend", response_model=list[TrendPoint])
def trend(freq: str = Query("D", pattern="^[DWM]$")):
    df = revenue_trend(freq)
    df = df.assign(period=df["period"].astype(str))
    return df.to_dict(orient="records")


@router.get("/regions", response_model=list[RegionRow])
def regions():
    return region_performance().to_dict(orient="records")


@router.get("/categories")
def categories():
    return category_performance().to_dict(orient="records")