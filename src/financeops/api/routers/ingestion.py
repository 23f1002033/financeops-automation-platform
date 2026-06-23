"""Ingestion endpoints — upload a file and trigger the ETL."""
from __future__ import annotations

import shutil

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from financeops.api.schemas import IngestResponse
from financeops.config import get_settings
from financeops.ingestion.loaders import ingest_file
from financeops.ingestion.validators import SCHEMAS

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
settings = get_settings()


@router.post("/upload", response_model=IngestResponse)
async def upload(
    dataset: str = Form(..., description="orders | returns"),
    file: UploadFile = File(...),
):
    if dataset not in SCHEMAS:
        raise HTTPException(400, f"Unknown dataset '{dataset}'. Expected {list(SCHEMAS)}")
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    dest = settings.raw_data_dir / file.filename
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        summary = ingest_file(dest, dataset)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    return IngestResponse(**{k: summary.get(k) for k in IngestResponse.model_fields})