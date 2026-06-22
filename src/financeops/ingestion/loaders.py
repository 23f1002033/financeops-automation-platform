"""File loaders and star-schema ETL — the single ingestion entry point."""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from financeops.config import get_settings
from financeops.db.models import (
    DimCustomer, DimDate, DimProduct, DimRegion,
    FactOrders, FactReturns, IngestionAudit,
)
from financeops.db.session import session_scope
from financeops.ingestion.quality import profile
from financeops.ingestion.validators import SCHEMAS, validate
from financeops.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def read_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix} ({path.name})")


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _already_loaded(session: Session, file_hash: str) -> bool:
    stmt = select(IngestionAudit).where(
        IngestionAudit.file_hash == file_hash,
        IngestionAudit.status.in_(("success", "partial")),
    )
    return session.execute(stmt).first() is not None


def _date_key(d: dt.date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def _upsert_date(session: Session, cache: dict, d: dt.date) -> int:
    dk = _date_key(d)
    if dk in cache:
        return dk
    if not session.get(DimDate, dk):
        session.add(DimDate(
            date_key=dk, full_date=d, day=d.day, week=int(d.isocalendar().week),
            month=d.month, month_name=d.strftime("%b"),
            quarter=(d.month - 1) // 3 + 1, year=d.year,
            is_weekend=1 if d.weekday() >= 5 else 0,
        ))
    cache[dk] = True
    return dk


def _get_or_create(session: Session, model, cache: dict, natural_key: str, key_field: str, **attrs) -> int:
    if natural_key in cache:
        return cache[natural_key]
    stmt = select(model).where(getattr(model, key_field) == natural_key)
    obj = session.execute(stmt).scalar_one_or_none()
    if obj is None:
        obj = model(**{key_field: natural_key}, **attrs)
        session.add(obj)
        session.flush()
    surrogate = getattr(obj, model.__mapper__.primary_key[0].name)
    cache[natural_key] = surrogate
    return surrogate


def _load_orders(session: Session, df: pd.DataFrame) -> int:
    date_cache, cust_cache, prod_cache, region_cache = {}, {}, {}, {}
    loaded = 0
    for _, r in df.iterrows():
        d = pd.to_datetime(r["order_date"]).date()
        dk = _upsert_date(session, date_cache, d)
        ck = _get_or_create(session, DimCustomer, cust_cache, str(r["customer_id"]), "customer_id",
                            segment=str(r.get("segment") or "Retail"))
        pk = _get_or_create(session, DimProduct, prod_cache, str(r["product_id"]), "product_id",
                            category=str(r.get("category") or "Unknown"),
                            subcategory=str(r.get("subcategory") or "Unknown"))
        rk = _get_or_create(session, DimRegion, region_cache, str(r["region_id"]), "region_id",
                            zone=str(r.get("zone") or "Unknown"),
                            state=str(r.get("state") or "Unknown"),
                            city=str(r.get("city") or "Unknown"))
        gross = float(r["gross_revenue"])
        disc = float(r.get("discount") or 0.0)
        session.add(FactOrders(
            order_id=str(r["order_id"]), date_key=dk, customer_key=ck,
            product_key=pk, region_key=rk, quantity=int(r["quantity"]),
            gross_revenue=gross, discount=disc, cost=float(r["cost"]),
            net_revenue=gross - disc,
        ))
        loaded += 1
    return loaded


def _load_returns(session: Session, df: pd.DataFrame) -> int:
    date_cache, region_cache = {}, {}
    loaded = 0
    for _, r in df.iterrows():
        d = pd.to_datetime(r["return_date"]).date()
        dk = _upsert_date(session, date_cache, d)
        rk = _get_or_create(session, DimRegion, region_cache, str(r["region_id"]), "region_id",
                            zone="Unknown", state="Unknown", city="Unknown")
        session.add(FactReturns(
            order_id=str(r["order_id"]), date_key=dk, region_key=rk,
            refund_amount=float(r["refund_amount"]), reason=str(r.get("reason") or "Unspecified"),
        ))
        loaded += 1
    return loaded


_DATE_COL = {"orders": "order_date", "returns": "return_date"}
_LOADERS = {"orders": _load_orders, "returns": _load_returns}


def ingest_file(path: str | Path, dataset: str) -> dict:
    """Full ingestion pipeline for a single file."""
    if dataset not in SCHEMAS:
        raise ValueError(f"Unknown dataset '{dataset}'. Expected one of {list(SCHEMAS)}")

    path = Path(path)
    logger.info("Ingesting %s as dataset '%s'", path.name, dataset)

    file_hash = _file_hash(path)
    with session_scope() as session:
        if _already_loaded(session, file_hash):
            logger.info("Skipping %s — identical file already loaded (idempotent)", path.name)
            return {"source_file": path.name, "dataset": dataset,
                    "status": "skipped_duplicate", "rows_loaded": 0, "rows_rejected": 0}

    raw = read_file(path)
    rows_received = len(raw)
    clean, rejected = validate(raw, SCHEMAS[dataset])
    qreport = profile(clean, dataset, _DATE_COL[dataset])
    logger.info("Quality report for %s: %s", dataset, qreport.to_dict())

    error_path = None
    if len(rejected):
        error_path = settings.processed_data_dir / f"{path.stem}__rejected.csv"
        rejected.to_csv(error_path, index=False)
        logger.warning("%d rows rejected -> %s", len(rejected), error_path)

    with session_scope() as session:
        loaded = _LOADERS[dataset](session, clean)
        status = "success" if not len(rejected) else ("partial" if loaded else "failed")
        session.add(IngestionAudit(
            source_file=path.name, file_hash=file_hash, dataset=dataset,
            rows_received=rows_received, rows_loaded=loaded, rows_rejected=len(rejected),
            status=status, message=f"quality_passed={qreport.passed}",
        ))

    summary = {
        "source_file": path.name, "dataset": dataset,
        "rows_received": rows_received, "rows_loaded": loaded,
        "rows_rejected": len(rejected), "status": status,
        "quality": qreport.to_dict(),
        "error_report": str(error_path) if error_path else None,
    }
    logger.info("Ingestion complete: %s", summary)
    return summary