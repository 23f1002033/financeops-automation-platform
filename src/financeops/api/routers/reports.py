"""Reporting endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from financeops.api.schemas import ReportResponse
from financeops.reporting.csv_export import export_csv_bundle
from financeops.reporting.executive_summary import build_summary
from financeops.reporting.pdf_report import generate_pdf_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/executive-summary")
def executive_summary():
    return build_summary()


@router.post("/generate", response_model=ReportResponse)
def generate():
    pdf = generate_pdf_report()
    csvs = export_csv_bundle()
    return ReportResponse(pdf_report=str(pdf), csv_reports=csvs)


@router.get("/download")
def download(path: str):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "Report not found")
    return FileResponse(p, filename=p.name)