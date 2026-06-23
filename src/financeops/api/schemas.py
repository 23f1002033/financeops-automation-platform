"""Pydantic request/response models for the API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    version: str
    environment: str


class IngestResponse(BaseModel):
    source_file: str
    dataset: str
    status: str
    rows_received: int | None = None
    rows_loaded: int | None = None
    rows_rejected: int | None = None
    error_report: str | None = None


class KpiSnapshotResponse(BaseModel):
    period_start: str
    period_end: str
    revenue: float
    gross_margin_pct: float
    orders: int
    unique_customers: int
    return_rate_pct: float
    refund_rate_pct: float
    retention_pct: float
    order_growth_pct: float


class TrendPoint(BaseModel):
    period: str
    revenue: float
    orders: int
    gross_margin_pct: float | None = None


class RegionRow(BaseModel):
    zone: str
    revenue: float
    orders: int
    gross_margin_pct: float


class AnomalyOut(BaseModel):
    metric: str
    date: str
    value: float
    expected: float
    deviation_pct: float
    direction: str
    severity: str
    method: str
    message: str


class ReportResponse(BaseModel):
    pdf_report: str | None = None
    csv_reports: dict[str, str] = Field(default_factory=dict)